"""
LLM-as-Judge 채점기

Claude API를 사용하여 에이전트 출력을 루브릭 기반으로 평가하는 채점기
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import structlog
from anthropic import AsyncAnthropic
from pydantic import BaseModel, Field

from backend.evals.graders.base import BaseGrader
from backend.evals.models.entities import GraderResult, Trial

logger = structlog.get_logger(__name__)


# ==================== 설정 모델 ====================


class LLMJudgeConfig(BaseModel):
    """LLM Judge 채점기 설정"""

    # 평가 루브릭 (마크다운 형식)
    rubric: str = Field(
        ...,
        description="평가 루브릭 (마크다운 형식으로 작성)",
    )

    # 평가 기준 목록
    criteria: list[str] = Field(
        default_factory=list,
        description="평가 기준 목록 (예: ['정확성', '완전성', '코드 품질'])",
    )

    # 점수 스케일 (1-5 또는 1-10)
    scoring_scale: int = Field(
        default=5,
        ge=2,
        le=10,
        description="점수 스케일 (2-10, 기본값 5)",
    )

    # Claude 모델
    model: str = Field(
        default="claude-sonnet-4-20250514",
        description="평가에 사용할 Claude 모델",
    )

    # Temperature (결정적 평가를 위해 0.0 권장)
    temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="LLM temperature (0.0 = 결정적)",
    )

    # 최대 토큰
    max_tokens: int = Field(
        default=2048,
        ge=256,
        le=8192,
        description="최대 출력 토큰 수",
    )

    # 캐싱 활성화 (동일 입/출력 재평가 방지)
    enable_cache: bool = Field(
        default=True,
        description="캐싱 활성화 여부",
    )

    # 통과 기준 점수 (0-1 스케일)
    pass_threshold: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="통과 기준 점수 (0-1 스케일)",
    )


# ==================== 평가 결과 모델 ====================


@dataclass
class CriterionScore:
    """개별 기준 점수"""

    criterion: str  # 평가 기준명
    score: int  # 원점수 (1-scale)
    max_score: int  # 최대 점수
    rationale: str  # 점수 근거
    improvement: str | None = None  # 개선 제안


@dataclass
class JudgeEvaluation:
    """LLM Judge 평가 결과"""

    overall_score: float  # 전체 점수 (0-1 스케일)
    criterion_scores: list[CriterionScore] = field(default_factory=list)
    summary: str = ""  # 전체 요약
    strengths: list[str] = field(default_factory=list)  # 강점
    weaknesses: list[str] = field(default_factory=list)  # 약점
    improvements: list[str] = field(default_factory=list)  # 개선 제안
    confidence: float = 0.9  # 평가 신뢰도


@dataclass
class TokenUsage:
    """토큰 사용량"""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0

    def add(self, other: "TokenUsage") -> "TokenUsage":
        """다른 사용량 추가"""
        return TokenUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
            cost_usd=self.cost_usd + other.cost_usd,
        )


# ==================== LLM Judge 채점기 ====================


class LLMJudgeGrader(BaseGrader):
    """
    LLM-as-Judge 채점기

    Claude API를 사용하여 에이전트 출력을 루브릭 기반으로 평가
    """

    grader_type = "llm_rubric"

    # Claude Sonnet 4 가격 (2024년 기준, USD per 1M tokens)
    PRICE_INPUT_PER_1M = 3.0
    PRICE_OUTPUT_PER_1M = 15.0

    def __init__(
        self,
        config: LLMJudgeConfig,
        grader_id: str | None = None,
        weight: float = 1.0,
        required: bool = False,
        description: str | None = None,
        api_key: str | None = None,
    ):
        """
        LLM Judge 채점기 초기화

        Args:
            config: LLMJudgeConfig 설정 객체
            grader_id: 채점기 고유 ID
            weight: 가중치 (0-1)
            required: 필수 통과 여부
            description: 채점기 설명
            api_key: Anthropic API 키 (미지정 시 환경변수 사용)
        """
        super().__init__(
            grader_id=grader_id or "llm_judge",
            weight=weight,
            required=required,
            description=description or "LLM-as-Judge 루브릭 기반 채점기",
        )

        self.config = config
        self.client = AsyncAnthropic(api_key=api_key) if api_key else AsyncAnthropic()
        self.logger = logger.bind(grader_id=self.grader_id)

        # 캐시 (메모리 기반)
        self._cache: dict[str, JudgeEvaluation] = {}

        # 누적 토큰 사용량
        self._total_usage = TokenUsage()

    async def grade(self, trial: Trial) -> GraderResult:
        """
        Trial을 채점하고 GraderResult 반환

        Args:
            trial: 채점 대상 Trial

        Returns:
            GraderResult: 채점 결과
        """
        start_time = time.perf_counter()

        try:
            # 에이전트 입력/출력 추출
            agent_input = self._extract_input(trial)
            agent_output = self._extract_output(trial)

            self.logger.info(
                "LLM Judge 채점 시작",
                trial_id=trial.trial_id,
                input_length=len(agent_input),
                output_length=len(agent_output),
            )

            # 캐시 확인
            cache_key = self._compute_cache_key(agent_input, agent_output)
            if self.config.enable_cache and cache_key in self._cache:
                self.logger.debug("캐시 히트", cache_key=cache_key[:16])
                evaluation = self._cache[cache_key]
                usage = TokenUsage()  # 캐시 사용 시 토큰 비용 없음
            else:
                # LLM 호출하여 평가
                evaluation, usage = await self._evaluate(agent_input, agent_output)

                # 캐시 저장
                if self.config.enable_cache:
                    self._cache[cache_key] = evaluation

                # 누적 사용량 업데이트
                self._total_usage = self._total_usage.add(usage)

            duration = time.perf_counter() - start_time

            # 통과 여부 판정
            passed = evaluation.overall_score >= self.config.pass_threshold

            # 부분 점수 생성
            partial_scores = {
                cs.criterion: cs.score / cs.max_score for cs in evaluation.criterion_scores
            }

            # 평가 프롬프트 및 응답 저장용 문자열 생성
            judge_prompt = self._build_prompt(agent_input, agent_output)
            judge_response = self._format_evaluation_response(evaluation)

            self.logger.info(
                "LLM Judge 채점 완료",
                trial_id=trial.trial_id,
                score=evaluation.overall_score,
                passed=passed,
                duration_seconds=duration,
                tokens_used=usage.total_tokens,
            )

            return GraderResult(
                trial_id=trial.trial_id,
                grader_id=self.grader_id,
                grader_type=self.grader_type,
                score=evaluation.overall_score,
                passed=passed,
                partial_scores=partial_scores,
                explanation=evaluation.summary,
                judge_model=self.config.model,
                judge_prompt=judge_prompt,
                judge_response=judge_response,
                confidence=evaluation.confidence,
                duration_seconds=duration,
                error_message=None,
                graded_at=datetime.now(),
            )

        except Exception as e:
            duration = time.perf_counter() - start_time
            self.logger.error(
                "LLM Judge 채점 실패",
                trial_id=trial.trial_id,
                error=str(e),
            )

            return self._create_result(
                trial_id=trial.trial_id,
                score=0.0,
                passed=False,
                explanation=f"LLM Judge 채점 중 오류 발생: {e}",
                duration_seconds=duration,
                error_message=str(e),
            )

    async def _evaluate(
        self, agent_input: str, agent_output: str
    ) -> tuple[JudgeEvaluation, TokenUsage]:
        """
        Claude API를 호출하여 평가 수행

        Args:
            agent_input: 에이전트 입력
            agent_output: 에이전트 출력

        Returns:
            (JudgeEvaluation, TokenUsage): 평가 결과 및 토큰 사용량
        """
        prompt = self._build_prompt(agent_input, agent_output)
        system_prompt = self._build_system_prompt()

        response = await self.client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )

        # 응답 파싱
        first_block = response.content[0]
        content = first_block.text if hasattr(first_block, "text") else ""

        # 토큰 사용량 계산
        usage = TokenUsage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            cost_usd=self._calculate_cost(
                response.usage.input_tokens, response.usage.output_tokens
            ),
        )

        # JSON 파싱
        evaluation = self._parse_evaluation_response(content)

        return evaluation, usage

    def _build_system_prompt(self) -> str:
        """시스템 프롬프트 생성"""
        return """당신은 AI 에이전트 출력을 평가하는 전문 심사관입니다.

역할:
- 제공된 루브릭과 평가 기준에 따라 에이전트 출력을 공정하게 평가합니다.
- 각 기준에 대해 점수와 구체적인 근거를 제공합니다.
- 객관적이고 일관된 평가를 수행합니다.

평가 원칙:
1. 루브릭에 명시된 기준만 사용합니다.
2. 점수는 반드시 근거와 함께 제공합니다.
3. 개선 가능한 부분을 구체적으로 제시합니다.
4. 에이전트의 강점과 약점을 균형 있게 평가합니다.

응답 형식:
반드시 JSON 형식으로 응답하세요. JSON 블록 외에 다른 텍스트는 포함하지 마세요."""

    def _build_prompt(self, agent_input: str, agent_output: str) -> str:
        """평가 프롬프트 생성"""
        criteria_list = "\n".join(f"- {criterion}" for criterion in self.config.criteria)

        return f"""## 평가 루브릭
{self.config.rubric}

## 평가 기준
{criteria_list}

## 점수 스케일
각 기준에 대해 1-{self.config.scoring_scale} 점수를 부여하세요.
- 1점: 매우 부족
- {self.config.scoring_scale // 2}점: 보통
- {self.config.scoring_scale}점: 우수

## 에이전트 입력
```
{agent_input}
```

## 에이전트 출력
```
{agent_output}
```

## 평가 지침
다음 JSON 형식으로 응답하세요:

```json
{{
  "criterion_scores": [
    {{
      "criterion": "기준명",
      "score": 점수(정수),
      "max_score": {self.config.scoring_scale},
      "rationale": "점수 근거 설명",
      "improvement": "개선 제안 (선택)"
    }}
  ],
  "summary": "전체 평가 요약",
  "strengths": ["강점1", "강점2"],
  "weaknesses": ["약점1", "약점2"],
  "improvements": ["개선 제안1", "개선 제안2"],
  "confidence": 0.0~1.0 사이의 평가 신뢰도
}}
```

각 기준({", ".join(self.config.criteria)})에 대해 반드시 점수와 근거를 제공하세요."""

    def _parse_evaluation_response(self, content: str) -> JudgeEvaluation:
        """
        LLM 응답에서 평가 결과 파싱

        Args:
            content: LLM 응답 텍스트

        Returns:
            JudgeEvaluation: 파싱된 평가 결과
        """
        import re

        # JSON 블록 추출
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        json_str = json_match.group(1).strip() if json_match else content.strip()

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            self.logger.warning("JSON 파싱 실패, 기본값 반환", error=str(e))
            return JudgeEvaluation(
                overall_score=0.0,
                summary="평가 응답 파싱 실패",
                confidence=0.0,
            )

        # 기준별 점수 파싱
        criterion_scores: list[CriterionScore] = []
        for cs_data in data.get("criterion_scores", []):
            criterion_scores.append(
                CriterionScore(
                    criterion=cs_data.get("criterion", ""),
                    score=cs_data.get("score", 1),
                    max_score=cs_data.get("max_score", self.config.scoring_scale),
                    rationale=cs_data.get("rationale", ""),
                    improvement=cs_data.get("improvement"),
                )
            )

        # 전체 점수 계산 (0-1 스케일)
        if criterion_scores:
            total_score = sum(cs.score for cs in criterion_scores)
            max_total = sum(cs.max_score for cs in criterion_scores)
            overall_score = total_score / max_total if max_total > 0 else 0.0
        else:
            overall_score = 0.0

        return JudgeEvaluation(
            overall_score=overall_score,
            criterion_scores=criterion_scores,
            summary=data.get("summary", ""),
            strengths=data.get("strengths", []),
            weaknesses=data.get("weaknesses", []),
            improvements=data.get("improvements", []),
            confidence=data.get("confidence", 0.9),
        )

    def _format_evaluation_response(self, evaluation: JudgeEvaluation) -> str:
        """평가 결과를 문자열로 포맷팅"""
        result = {
            "overall_score": evaluation.overall_score,
            "criterion_scores": [
                {
                    "criterion": cs.criterion,
                    "score": cs.score,
                    "max_score": cs.max_score,
                    "rationale": cs.rationale,
                    "improvement": cs.improvement,
                }
                for cs in evaluation.criterion_scores
            ],
            "summary": evaluation.summary,
            "strengths": evaluation.strengths,
            "weaknesses": evaluation.weaknesses,
            "improvements": evaluation.improvements,
            "confidence": evaluation.confidence,
        }
        return json.dumps(result, ensure_ascii=False, indent=2)

    def _extract_input(self, trial: Trial) -> str:
        """Trial에서 에이전트 입력 추출"""
        # Trial의 환경 설정이나 초기 메시지에서 입력 추출
        # 실제 구현에서는 Trial 구조에 맞게 조정 필요
        inputs = trial.env_snapshot_id or ""

        # 추가 입력 정보가 있을 수 있음
        # Trial에 messages나 initial_state 등이 있다면 활용
        return inputs

    def _extract_output(self, trial: Trial) -> str:
        """Trial에서 에이전트 출력 추출"""
        # grader_results에서 이전 결과를 참조하거나
        # Trial의 transcript/outcome에서 최종 출력 추출
        outputs: list[str] = []

        # grader_results에서 관련 정보 추출
        for result in trial.grader_results:
            if result.get("explanation"):
                outputs.append(str(result["explanation"]))

        return "\n".join(outputs) if outputs else ""

    def _compute_cache_key(self, agent_input: str, agent_output: str) -> str:
        """캐시 키 계산"""
        # 입력, 출력, 루브릭을 조합하여 해시 생성
        content = f"{agent_input}|{agent_output}|{self.config.rubric}"
        return hashlib.sha256(content.encode()).hexdigest()

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """토큰 비용 계산 (USD)"""
        input_cost = (input_tokens / 1_000_000) * self.PRICE_INPUT_PER_1M
        output_cost = (output_tokens / 1_000_000) * self.PRICE_OUTPUT_PER_1M
        return input_cost + output_cost

    def get_total_usage(self) -> TokenUsage:
        """누적 토큰 사용량 반환"""
        return self._total_usage

    def clear_cache(self) -> int:
        """캐시 초기화 및 삭제된 항목 수 반환"""
        count = len(self._cache)
        self._cache.clear()
        return count

    def validate_config(self) -> list[str]:
        """설정 유효성 검사"""
        errors = super().validate_config()

        if not self.config.rubric:
            errors.append("루브릭이 비어있습니다")

        if not self.config.criteria:
            errors.append("평가 기준이 지정되지 않았습니다")

        if self.config.scoring_scale < 2:
            errors.append("점수 스케일은 최소 2 이상이어야 합니다")

        return errors

    def to_dict(self) -> dict[str, Any]:
        """채점기 정보를 딕셔너리로 반환"""
        base = super().to_dict()
        base.update(
            {
                "config": {
                    "rubric": self.config.rubric[:100] + "..."
                    if len(self.config.rubric) > 100
                    else self.config.rubric,
                    "criteria": self.config.criteria,
                    "scoring_scale": self.config.scoring_scale,
                    "model": self.config.model,
                    "temperature": self.config.temperature,
                    "pass_threshold": self.config.pass_threshold,
                    "enable_cache": self.config.enable_cache,
                },
                "total_usage": {
                    "input_tokens": self._total_usage.input_tokens,
                    "output_tokens": self._total_usage.output_tokens,
                    "total_tokens": self._total_usage.total_tokens,
                    "cost_usd": self._total_usage.cost_usd,
                },
            }
        )
        return base


# ==================== 편의 함수 ====================


def create_llm_judge_grader(
    rubric: str,
    criteria: list[str],
    scoring_scale: int = 5,
    model: str = "claude-sonnet-4-20250514",
    temperature: float = 0.0,
    pass_threshold: float = 0.6,
    grader_id: str = "llm_judge",
    weight: float = 1.0,
    required: bool = False,
    description: str | None = None,
) -> LLMJudgeGrader:
    """
    LLM Judge 채점기 생성 편의 함수

    Args:
        rubric: 평가 루브릭 (마크다운)
        criteria: 평가 기준 목록
        scoring_scale: 점수 스케일 (기본 5)
        model: Claude 모델 (기본 sonnet)
        temperature: LLM temperature (기본 0.0)
        pass_threshold: 통과 기준 점수 (기본 0.6)
        grader_id: 채점기 ID
        weight: 가중치
        required: 필수 통과 여부
        description: 설명

    Returns:
        LLMJudgeGrader: 생성된 채점기
    """
    config = LLMJudgeConfig(
        rubric=rubric,
        criteria=criteria,
        scoring_scale=scoring_scale,
        model=model,
        temperature=temperature,
        pass_threshold=pass_threshold,
    )

    return LLMJudgeGrader(
        config=config,
        grader_id=grader_id,
        weight=weight,
        required=required,
        description=description,
    )

"""
트랜스크립트 메트릭 채점기 (Transcript Metrics Grader)

트랜스크립트 기반 메트릭 분석 채점기 구현
"""

import time
from typing import Any

import structlog

from backend.evals.graders.base import BaseGrader
from backend.evals.models.entities import GraderResult, Trial
from backend.evals.models.enums import GraderType

logger = structlog.get_logger(__name__)


class TranscriptMetricsGrader(BaseGrader):
    """
    트랜스크립트 기반 메트릭 채점기

    트랜스크립트를 분석하여 턴 수, 도구 호출 수, 에러 수 등을 기준으로 채점
    """

    grader_type: str = GraderType.TRANSCRIPT_METRICS.value

    def __init__(
        self,
        max_turns: int = 20,
        max_tool_calls: int = 50,
        max_errors: int = 3,
        max_retries: int = 5,
        efficiency_score: bool = True,
        thresholds: dict[str, int | float] | None = None,
        grader_id: str | None = None,
        weight: float = 1.0,
        required: bool = False,
        description: str | None = None,
    ):
        """
        TranscriptMetricsGrader 초기화

        Args:
            max_turns: 최대 허용 턴 수
            max_tool_calls: 최대 허용 도구 호출 수
            max_errors: 최대 허용 에러 수
            max_retries: 최대 허용 재시도 수
            efficiency_score: 효율성 점수 계산 여부
            thresholds: 추가 임계값 설정
            grader_id: 채점기 ID
            weight: 가중치
            required: 필수 통과 여부
            description: 설명
        """
        super().__init__(grader_id, weight, required, description)
        self.max_turns = max_turns
        self.max_tool_calls = max_tool_calls
        self.max_errors = max_errors
        self.max_retries = max_retries
        self.efficiency_score = efficiency_score
        self.thresholds = thresholds or {}

    async def grade(self, trial: Trial) -> GraderResult:
        """트랜스크립트 분석 및 채점"""
        start_time = time.perf_counter()

        logger.info(
            "트랜스크립트 메트릭 분석 시작",
            trial_id=trial.trial_id,
        )

        # Trial에서 트랜스크립트 정보 추출
        # Trial은 grader_results에 트랜스크립트 정보를 포함할 수 있음
        transcript_data = self._extract_transcript_data(trial)

        # 메트릭 추출
        metrics = self._calculate_metrics(transcript_data)

        # 각 메트릭 평가
        evaluations = self._evaluate_metrics(metrics)

        duration = time.perf_counter() - start_time

        # 최종 점수 계산
        passed_count = sum(1 for e in evaluations.values() if e["passed"])
        total_checks = len(evaluations)

        # 기본 점수: 통과율
        base_score = passed_count / total_checks if total_checks > 0 else 0.0

        # 효율성 점수 반영
        if self.efficiency_score:
            efficiency = self._calculate_efficiency_score(metrics)
            score = (base_score * 0.7) + (efficiency * 0.3)
        else:
            score = base_score

        # 필수 조건 체크 (에러 수 초과 시 무조건 실패)
        passed = (
            evaluations.get("errors", {}).get("passed", True) and passed_count >= total_checks * 0.5
        )

        # 부분 점수
        partial_scores: dict[str, float] = {
            "turns_score": evaluations.get("turns", {}).get("score", 0.0),
            "tool_calls_score": evaluations.get("tool_calls", {}).get("score", 0.0),
            "errors_score": evaluations.get("errors", {}).get("score", 0.0),
            "retries_score": evaluations.get("retries", {}).get("score", 0.0),
        }

        if self.efficiency_score:
            partial_scores["efficiency_score"] = self._calculate_efficiency_score(metrics)

        # 설명 생성
        explanation = self._generate_explanation(metrics, evaluations)

        logger.info(
            "트랜스크립트 메트릭 분석 완료",
            trial_id=trial.trial_id,
            metrics=metrics,
            passed=passed,
            score=score,
        )

        return self._create_result(
            trial_id=trial.trial_id,
            score=score,
            passed=passed,
            explanation=explanation,
            partial_scores=partial_scores,
            duration_seconds=duration,
        )

    def _extract_transcript_data(self, trial: Trial) -> dict[str, Any]:
        """Trial에서 트랜스크립트 데이터 추출"""
        # Trial에 직접 포함된 트랜스크립트 정보 사용
        # 실제 구현에서는 Trial과 연결된 Transcript 엔터티를 조회해야 함

        # Trial의 grader_results에서 이전 트랜스크립트 정보 추출 시도
        for result in trial.grader_results:
            if result.get("grader_type") == "transcript":
                return result.get("data", {})

        # 기본 구조 반환 (Trial 메트릭 기반 추정)
        return {
            "messages": [],
            "tool_calls": [],
            "n_turns": 0,
            "n_tool_calls": 0,
            "n_errors": 0,
            "n_retries": 0,
        }

    def _calculate_metrics(self, transcript_data: dict[str, Any]) -> dict[str, int]:
        """트랜스크립트에서 메트릭 계산"""
        messages = transcript_data.get("messages", [])
        tool_calls = transcript_data.get("tool_calls", [])

        # 턴 수 계산 (assistant 메시지 기준)
        n_turns = transcript_data.get("n_turns", 0)
        if n_turns == 0:
            n_turns = sum(1 for m in messages if m.get("role") == "assistant")

        # 도구 호출 수
        n_tool_calls = transcript_data.get("n_tool_calls", 0)
        if n_tool_calls == 0:
            n_tool_calls = len(tool_calls)

        # 에러 수 계산
        n_errors = transcript_data.get("n_errors", 0)
        if n_errors == 0:
            # 도구 호출 결과에서 에러 카운트
            for call in tool_calls:
                if call.get("error") or call.get("is_error"):
                    n_errors += 1
            # 메시지에서 에러 패턴 검색
            for msg in messages:
                content = msg.get("content", "")
                if isinstance(content, str):
                    if "error" in content.lower() or "exception" in content.lower():
                        n_errors += 1

        # 재시도 수
        n_retries = transcript_data.get("n_retries", 0)

        return {
            "turns": n_turns,
            "tool_calls": n_tool_calls,
            "errors": n_errors,
            "retries": n_retries,
        }

    def _evaluate_metrics(self, metrics: dict[str, int]) -> dict[str, dict[str, Any]]:
        """각 메트릭 평가"""
        evaluations: dict[str, dict[str, Any]] = {}

        # 턴 수 평가
        turns = metrics["turns"]
        turns_passed = turns <= self.max_turns
        turns_score = max(
            0.0, 1.0 - (turns / (self.max_turns * 2)) if turns > self.max_turns else 1.0
        )
        evaluations["turns"] = {
            "value": turns,
            "max": self.max_turns,
            "passed": turns_passed,
            "score": turns_score,
            "message": f"턴 수: {turns}/{self.max_turns}",
        }

        # 도구 호출 수 평가
        tool_calls = metrics["tool_calls"]
        tool_calls_passed = tool_calls <= self.max_tool_calls
        tool_calls_score = max(
            0.0,
            1.0 - (tool_calls / (self.max_tool_calls * 2))
            if tool_calls > self.max_tool_calls
            else 1.0,
        )
        evaluations["tool_calls"] = {
            "value": tool_calls,
            "max": self.max_tool_calls,
            "passed": tool_calls_passed,
            "score": tool_calls_score,
            "message": f"도구 호출: {tool_calls}/{self.max_tool_calls}",
        }

        # 에러 수 평가
        errors = metrics["errors"]
        errors_passed = errors <= self.max_errors
        errors_score = max(0.0, 1.0 - (errors / (self.max_errors + 1)))
        evaluations["errors"] = {
            "value": errors,
            "max": self.max_errors,
            "passed": errors_passed,
            "score": errors_score,
            "message": f"에러: {errors}/{self.max_errors}",
        }

        # 재시도 수 평가
        retries = metrics["retries"]
        retries_passed = retries <= self.max_retries
        retries_score = max(0.0, 1.0 - (retries / (self.max_retries + 1)))
        evaluations["retries"] = {
            "value": retries,
            "max": self.max_retries,
            "passed": retries_passed,
            "score": retries_score,
            "message": f"재시도: {retries}/{self.max_retries}",
        }

        # 추가 임계값 평가
        for key, threshold in self.thresholds.items():
            if key not in metrics:
                continue
            value = metrics[key]
            threshold_val = float(threshold)
            passed = value <= threshold_val
            score_val = max(
                0.0, 1.0 - (value / (threshold_val * 2)) if value > threshold_val else 1.0
            )
            evaluations[key] = {
                "value": value,
                "max": threshold_val,
                "passed": passed,
                "score": score_val,
                "message": f"{key}: {value}/{threshold_val}",
            }

        return evaluations

    def _calculate_efficiency_score(self, metrics: dict[str, int]) -> float:
        """효율성 점수 계산"""
        # 효율성: 최소 리소스로 목표 달성 정도
        # 낮은 턴 수, 낮은 도구 호출 수, 낮은 에러 수가 좋음

        turns_efficiency = 1.0 - min(1.0, metrics["turns"] / (self.max_turns * 2))
        tool_calls_efficiency = 1.0 - min(1.0, metrics["tool_calls"] / (self.max_tool_calls * 2))
        error_penalty = min(1.0, metrics["errors"] / (self.max_errors + 1))
        retry_penalty = min(1.0, metrics["retries"] / (self.max_retries + 1))

        # 가중 평균 (에러와 재시도는 패널티로 적용)
        efficiency = (
            (turns_efficiency * 0.3)
            + (tool_calls_efficiency * 0.3)
            + ((1.0 - error_penalty) * 0.25)
            + ((1.0 - retry_penalty) * 0.15)
        )

        return max(0.0, min(1.0, efficiency))

    def _generate_explanation(
        self,
        metrics: dict[str, int],
        evaluations: dict[str, dict[str, Any]],
    ) -> str:
        """설명 생성"""
        lines = ["트랜스크립트 메트릭 분석 결과:"]

        for _key, eval_data in evaluations.items():
            status = "PASS" if eval_data["passed"] else "FAIL"
            lines.append(f"  - [{status}] {eval_data['message']}")

        if self.efficiency_score:
            efficiency = self._calculate_efficiency_score(metrics)
            lines.append(f"  - 효율성 점수: {efficiency:.2f}")

        # 실패한 항목 강조
        failed = [k for k, v in evaluations.items() if not v["passed"]]
        if failed:
            lines.append(f"\n주의: {', '.join(failed)} 항목이 임계값 초과")

        return "\n".join(lines)

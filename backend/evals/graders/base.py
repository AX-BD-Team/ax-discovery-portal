"""
채점기 기본 클래스

모든 채점기가 상속받는 추상 베이스 클래스
"""

import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

import structlog

from backend.evals.models.entities import GraderResult, Trial

logger = structlog.get_logger(__name__)


class BaseGrader(ABC):
    """
    채점기 기본 클래스

    모든 채점기 구현은 이 클래스를 상속받아야 합니다.
    """

    grader_id: str
    grader_type: str
    weight: float = 1.0
    required: bool = False
    description: str | None = None

    def __init__(
        self,
        grader_id: str | None = None,
        weight: float = 1.0,
        required: bool = False,
        description: str | None = None,
    ):
        """
        채점기 초기화

        Args:
            grader_id: 채점기 고유 ID (미지정 시 클래스명 사용)
            weight: 가중치 (0-1)
            required: 필수 통과 여부
            description: 채점기 설명
        """
        self.grader_id = grader_id or self.__class__.__name__
        self.weight = weight
        self.required = required
        self.description = description

    @abstractmethod
    async def grade(self, trial: Trial) -> GraderResult:
        """
        Trial을 채점하고 GraderResult 반환

        Args:
            trial: 채점 대상 Trial

        Returns:
            GraderResult: 채점 결과
        """
        ...

    def _create_result(
        self,
        trial_id: str,
        score: float,
        passed: bool,
        explanation: str = "",
        partial_scores: dict[str, float] | None = None,
        duration_seconds: float = 0.0,
        error_message: str | None = None,
    ) -> GraderResult:
        """
        GraderResult 생성 헬퍼

        Args:
            trial_id: Trial ID
            score: 점수 (0-1)
            passed: 통과 여부
            explanation: 채점 설명/근거
            partial_scores: 항목별 부분 점수
            duration_seconds: 채점 소요 시간
            error_message: 에러 메시지

        Returns:
            GraderResult: 채점 결과 객체
        """
        return GraderResult(
            trial_id=trial_id,
            grader_id=self.grader_id,
            grader_type=self.grader_type,
            score=score,
            passed=passed,
            partial_scores=partial_scores or {},
            explanation=explanation,
            # LLM Judge 필드는 결정적 채점기에서 사용하지 않음
            judge_model=None,
            judge_prompt=None,
            judge_response=None,
            confidence=None,
            duration_seconds=duration_seconds,
            error_message=error_message,
            graded_at=datetime.now(),
        )

    async def safe_grade(self, trial: Trial) -> GraderResult:
        """
        예외 처리가 포함된 안전한 채점 실행

        Args:
            trial: 채점 대상 Trial

        Returns:
            GraderResult: 채점 결과 (에러 발생 시 실패 결과)
        """
        start_time = time.perf_counter()
        try:
            result = await self.grade(trial)
            return result
        except Exception as e:
            duration = time.perf_counter() - start_time
            logger.error(
                "채점 중 에러 발생",
                grader_id=self.grader_id,
                trial_id=trial.trial_id,
                error=str(e),
            )
            return self._create_result(
                trial_id=trial.trial_id,
                score=0.0,
                passed=False,
                explanation=f"채점 중 에러 발생: {e}",
                duration_seconds=duration,
                error_message=str(e),
            )

    def validate_config(self) -> list[str]:
        """
        설정 유효성 검사

        Returns:
            list[str]: 유효성 오류 메시지 목록 (빈 리스트면 유효)
        """
        errors: list[str] = []
        if not self.grader_id:
            errors.append("grader_id가 비어있습니다")
        if not 0 <= self.weight <= 1:
            errors.append(f"weight는 0-1 범위여야 합니다: {self.weight}")
        return errors

    def to_dict(self) -> dict[str, Any]:
        """
        채점기 정보를 딕셔너리로 반환

        Returns:
            dict: 채점기 정보
        """
        return {
            "grader_id": self.grader_id,
            "grader_type": self.grader_type,
            "weight": self.weight,
            "required": self.required,
            "description": self.description,
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.grader_id}, type={self.grader_type})"

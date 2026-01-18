"""
채점기 팩토리 (Grader Factory)

GraderConfig로부터 채점기 인스턴스 생성
"""

from typing import Any

import structlog

from backend.evals.graders.base import BaseGrader
from backend.evals.graders.deterministic import MypyGrader, PytestGrader, RuffGrader
from backend.evals.graders.llm_judge import LLMJudgeConfig, LLMJudgeGrader
from backend.evals.graders.state_check import StateCheckGrader
from backend.evals.graders.tool_call_check import ToolCallCheckGrader
from backend.evals.graders.transcript_metrics import TranscriptMetricsGrader
from backend.evals.models.configs import GraderConfig
from backend.evals.models.enums import GraderType

logger = structlog.get_logger(__name__)


class GraderFactory:
    """
    채점기 팩토리

    GraderConfig를 기반으로 적절한 채점기 인스턴스 생성
    """

    # 채점기 타입별 클래스 매핑
    _grader_map: dict[GraderType, type[BaseGrader]] = {
        GraderType.DETERMINISTIC_TESTS: PytestGrader,
        GraderType.STATE_CHECK: StateCheckGrader,
        GraderType.TRANSCRIPT_METRICS: TranscriptMetricsGrader,
        GraderType.TOOL_CALL_CHECK: ToolCallCheckGrader,
        GraderType.STATIC_ANALYSIS: RuffGrader,  # 기본 정적 분석 도구
        GraderType.LLM_RUBRIC: LLMJudgeGrader,  # LLM-as-Judge 채점기
    }

    # 정적 분석 도구별 클래스 매핑
    _static_analysis_map: dict[str, type[BaseGrader]] = {
        "ruff": RuffGrader,
        "mypy": MypyGrader,
    }

    @classmethod
    def create(cls, config: GraderConfig) -> BaseGrader:
        """
        GraderConfig로부터 채점기 인스턴스 생성

        Args:
            config: 채점기 설정

        Returns:
            BaseGrader: 생성된 채점기 인스턴스

        Raises:
            ValueError: 지원하지 않는 채점기 타입
        """
        grader_type = config.type

        logger.debug(
            "채점기 생성",
            grader_type=grader_type.value,
            grader_id=config.id,
        )

        # 정적 분석의 경우 도구별로 분기
        if grader_type == GraderType.STATIC_ANALYSIS:
            return cls._create_static_analysis_grader(config)

        grader_class = cls._grader_map.get(grader_type)

        if grader_class is None:
            # LLM_RUBRIC은 구현됨, 나머지 LLM 채점기는 아직 미구현
            if grader_type in (
                GraderType.LLM_ASSERTION,
                GraderType.LLM_PAIRWISE,
                GraderType.LLM_REFERENCE,
            ):
                raise NotImplementedError(
                    f"LLM 채점기 미구현: {grader_type.value}. 향후 버전에서 지원 예정입니다."
                )

            if grader_type == GraderType.HUMAN_REVIEW:
                raise NotImplementedError("인간 리뷰 채점기 미구현. 향후 버전에서 지원 예정입니다.")

            raise ValueError(f"지원하지 않는 채점기 타입: {grader_type.value}")

        # 채점기 인스턴스 생성
        return cls._instantiate_grader(grader_class, config)

    @classmethod
    def _create_static_analysis_grader(cls, config: GraderConfig) -> BaseGrader:
        """정적 분석 채점기 생성"""
        grader_config = config.config

        # 도구 결정
        tool = grader_config.get("tool", "ruff").lower()
        grader_class = cls._static_analysis_map.get(tool, RuffGrader)

        return cls._instantiate_grader(grader_class, config)

    @classmethod
    def _instantiate_grader(
        cls, grader_class: type[BaseGrader], config: GraderConfig
    ) -> BaseGrader:
        """채점기 인스턴스화"""
        grader_config = config.config

        # 공통 인자
        common_kwargs: dict[str, Any] = {
            "grader_id": config.id,
            "weight": config.weight,
            "required": config.required,
            "description": config.description,
        }

        # 채점기별 인자 매핑
        if grader_class == PytestGrader:
            return PytestGrader(
                test_paths=grader_config.get("test_files", ["tests/"]),
                pytest_args=grader_config.get("pytest_args", ["-v", "--tb=short"]),
                working_dir=grader_config.get("working_dir"),
                timeout_seconds=grader_config.get("timeout_seconds", 120),
                fail_fast=grader_config.get("fail_fast", False),
                coverage_threshold=grader_config.get("coverage_threshold"),
                **common_kwargs,
            )

        elif grader_class == RuffGrader:
            return RuffGrader(
                target_paths=grader_config.get("target_paths", ["."]),
                config_file=grader_config.get("config_file"),
                max_errors=grader_config.get("max_errors", 0),
                allow_warnings=grader_config.get("allow_warnings", False),
                timeout_seconds=grader_config.get("timeout_seconds", 120),
                **common_kwargs,
            )

        elif grader_class == MypyGrader:
            return MypyGrader(
                target_paths=grader_config.get("target_paths", ["."]),
                config_file=grader_config.get("config_file"),
                max_errors=grader_config.get("max_errors", 0),
                strict=grader_config.get("strict", False),
                timeout_seconds=grader_config.get("timeout_seconds", 120),
                **common_kwargs,
            )

        elif grader_class == StateCheckGrader:
            return StateCheckGrader(
                checks=grader_config.get("checks", []),
                timeout_seconds=grader_config.get("timeout_seconds", 60),
                **common_kwargs,
            )

        elif grader_class == TranscriptMetricsGrader:
            thresholds = grader_config.get("thresholds", {})
            return TranscriptMetricsGrader(
                max_turns=thresholds.get("max_turns", 20),
                max_tool_calls=thresholds.get("max_tool_calls", 50),
                max_errors=thresholds.get("max_errors", 3),
                max_retries=thresholds.get("max_retries", 5),
                efficiency_score=grader_config.get("efficiency_score", True),
                thresholds=thresholds,
                **common_kwargs,
            )

        elif grader_class == ToolCallCheckGrader:
            return ToolCallCheckGrader(
                required_tools=grader_config.get("required_tools", []),
                forbidden_tools=grader_config.get("forbidden_tools", []),
                expected_sequence=grader_config.get("call_order", []),
                min_calls={
                    r["tool"]: r.get("min_count", 1)
                    for r in grader_config.get("required_calls", [])
                },
                max_calls={
                    r["tool"]: r["max_count"]
                    for r in grader_config.get("required_calls", [])
                    if r.get("max_count") is not None
                },
                check_order=grader_config.get("check_order", False),
                **common_kwargs,
            )

        elif grader_class == LLMJudgeGrader:
            # LLM-as-Judge 채점기 생성
            llm_config = LLMJudgeConfig(
                rubric=grader_config.get("rubric", ""),
                criteria=grader_config.get("criteria", []),
                scoring_scale=grader_config.get("scoring_scale", 5),
                model=grader_config.get("model", "claude-sonnet-4-20250514"),
                temperature=grader_config.get("temperature", 0.0),
                max_tokens=grader_config.get("max_tokens", 2048),
                enable_cache=grader_config.get("enable_cache", True),
                pass_threshold=grader_config.get("pass_threshold", 0.6),
            )
            return LLMJudgeGrader(
                config=llm_config,
                api_key=grader_config.get("api_key"),
                **common_kwargs,
            )

        else:
            # 기본 생성
            logger.warning(
                "알 수 없는 채점기 클래스, 기본 인자로 생성",
                grader_class=grader_class.__name__,
            )
            return grader_class(**common_kwargs)

    @classmethod
    def create_all(cls, configs: list[GraderConfig]) -> list[BaseGrader]:
        """
        여러 채점기 설정으로부터 채점기 목록 생성

        Args:
            configs: 채점기 설정 목록

        Returns:
            list[BaseGrader]: 채점기 인스턴스 목록
        """
        graders: list[BaseGrader] = []

        for config in configs:
            if not config.enabled:
                logger.debug(
                    "채점기 비활성화됨",
                    grader_id=config.id,
                    grader_type=config.type.value,
                )
                continue

            try:
                grader = cls.create(config)
                graders.append(grader)
            except (ValueError, NotImplementedError) as e:
                logger.warning(
                    "채점기 생성 실패",
                    grader_id=config.id,
                    error=str(e),
                )

        return graders

    @classmethod
    def get_supported_types(cls) -> list[str]:
        """지원하는 채점기 타입 목록 반환"""
        return [t.value for t in cls._grader_map]

    @classmethod
    def is_supported(cls, grader_type: GraderType) -> bool:
        """해당 채점기 타입 지원 여부 확인"""
        return grader_type in cls._grader_map


def create_grader(config: GraderConfig) -> BaseGrader:
    """
    GraderConfig로부터 채점기 인스턴스 생성 (편의 함수)

    Args:
        config: 채점기 설정

    Returns:
        BaseGrader: 생성된 채점기 인스턴스
    """
    return GraderFactory.create(config)


def create_graders(configs: list[GraderConfig]) -> list[BaseGrader]:
    """
    여러 채점기 설정으로부터 채점기 목록 생성 (편의 함수)

    Args:
        configs: 채점기 설정 목록

    Returns:
        list[BaseGrader]: 채점기 인스턴스 목록
    """
    return GraderFactory.create_all(configs)

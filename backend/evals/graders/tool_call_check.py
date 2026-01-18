"""
도구 호출 검증 채점기 (Tool Call Check Grader)

도구 호출 패턴 검증 기반 채점기 구현
"""

import re
import time
from typing import Any

import structlog

from backend.evals.graders.base import BaseGrader
from backend.evals.models.entities import GraderResult, Trial
from backend.evals.models.enums import GraderType

logger = structlog.get_logger(__name__)


class ToolCallCheckGrader(BaseGrader):
    """
    도구 호출 패턴 검증 채점기

    필수 도구 호출, 금지 도구, 호출 순서 등을 검증하여 채점
    """

    grader_type: str = GraderType.TOOL_CALL_CHECK.value

    def __init__(
        self,
        required_tools: list[str] | None = None,
        forbidden_tools: list[str] | None = None,
        expected_sequence: list[str] | None = None,
        min_calls: dict[str, int] | None = None,
        max_calls: dict[str, int] | None = None,
        args_patterns: dict[str, dict[str, Any]] | None = None,
        check_order: bool = False,
        grader_id: str | None = None,
        weight: float = 1.0,
        required: bool = False,
        description: str | None = None,
    ):
        """
        ToolCallCheckGrader 초기화

        Args:
            required_tools: 반드시 호출해야 하는 도구 목록
            forbidden_tools: 호출하면 안 되는 도구 목록
            expected_sequence: 기대하는 호출 순서 (부분 순서)
            min_calls: 도구별 최소 호출 횟수
            max_calls: 도구별 최대 호출 횟수
            args_patterns: 도구별 인자 패턴 검증 규칙
            check_order: 순서 검증 여부 (false 권장)
            grader_id: 채점기 ID
            weight: 가중치
            required: 필수 통과 여부
            description: 설명
        """
        super().__init__(grader_id, weight, required, description)
        self.required_tools = required_tools or []
        self.forbidden_tools = forbidden_tools or []
        self.expected_sequence = expected_sequence or []
        self.min_calls = min_calls or {}
        self.max_calls = max_calls or {}
        self.args_patterns = args_patterns or {}
        self.check_order = check_order

    async def grade(self, trial: Trial) -> GraderResult:
        """도구 호출 패턴 검증 및 채점"""
        start_time = time.perf_counter()

        logger.info(
            "도구 호출 검증 시작",
            trial_id=trial.trial_id,
            required_tools=self.required_tools,
            forbidden_tools=self.forbidden_tools,
        )

        # Trial에서 도구 호출 정보 추출
        tool_calls = self._extract_tool_calls(trial)

        # 각 검증 수행
        validations: list[dict[str, Any]] = []

        # 1. 필수 도구 검증
        required_result = self._validate_required_tools(tool_calls)
        validations.append(required_result)

        # 2. 금지 도구 검증
        forbidden_result = self._validate_forbidden_tools(tool_calls)
        validations.append(forbidden_result)

        # 3. 호출 순서 검증 (옵션)
        if self.check_order and self.expected_sequence:
            sequence_result = self._validate_sequence(tool_calls)
            validations.append(sequence_result)

        # 4. 호출 횟수 검증
        count_result = self._validate_call_counts(tool_calls)
        validations.append(count_result)

        # 5. 인자 패턴 검증
        if self.args_patterns:
            args_result = self._validate_args_patterns(tool_calls)
            validations.append(args_result)

        duration = time.perf_counter() - start_time

        # 결과 집계
        passed_count = sum(1 for v in validations if v["passed"])
        total_checks = len(validations)

        # 점수 계산
        score = passed_count / total_checks if total_checks > 0 else 0.0

        # 필수 통과 조건: required/forbidden 검증은 반드시 통과해야 함
        required_passed = required_result["passed"] and forbidden_result["passed"]
        passed = required_passed and score >= 0.5

        # 부분 점수
        partial_scores: dict[str, float] = {
            "required_tools": 1.0 if required_result["passed"] else 0.0,
            "forbidden_tools": 1.0 if forbidden_result["passed"] else 0.0,
            "call_counts": 1.0 if count_result["passed"] else 0.0,
        }

        if self.check_order and self.expected_sequence:
            partial_scores["sequence"] = 1.0 if validations[2]["passed"] else 0.0

        if self.args_patterns:
            partial_scores["args_patterns"] = 1.0 if args_result["passed"] else 0.0

        # 설명 생성
        explanation = self._generate_explanation(tool_calls, validations)

        logger.info(
            "도구 호출 검증 완료",
            trial_id=trial.trial_id,
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

    def _extract_tool_calls(self, trial: Trial) -> list[dict[str, Any]]:
        """Trial에서 도구 호출 정보 추출"""
        tool_calls: list[dict[str, Any]] = []

        # Trial의 grader_results에서 도구 호출 정보 추출
        for result in trial.grader_results:
            if "tool_calls" in result:
                tool_calls.extend(result["tool_calls"])

        # 없으면 빈 리스트 반환
        return tool_calls

    def _validate_required_tools(self, tool_calls: list[dict[str, Any]]) -> dict[str, Any]:
        """필수 도구 호출 검증"""
        if not self.required_tools:
            return {"name": "required_tools", "passed": True, "message": "필수 도구 없음"}

        called_tools = {call.get("name", call.get("tool", "")) for call in tool_calls}
        missing = [t for t in self.required_tools if t not in called_tools]

        passed = len(missing) == 0
        if passed:
            message = f"필수 도구 모두 호출됨: {', '.join(self.required_tools)}"
        else:
            message = f"미호출 필수 도구: {', '.join(missing)}"

        return {
            "name": "required_tools",
            "passed": passed,
            "missing": missing,
            "message": message,
        }

    def _validate_forbidden_tools(self, tool_calls: list[dict[str, Any]]) -> dict[str, Any]:
        """금지 도구 호출 검증"""
        if not self.forbidden_tools:
            return {"name": "forbidden_tools", "passed": True, "message": "금지 도구 없음"}

        called_tools = {call.get("name", call.get("tool", "")) for call in tool_calls}
        violations = [t for t in self.forbidden_tools if t in called_tools]

        passed = len(violations) == 0
        message = "금지 도구 호출 없음" if passed else f"금지 도구 호출됨: {', '.join(violations)}"

        return {
            "name": "forbidden_tools",
            "passed": passed,
            "violations": violations,
            "message": message,
        }

    def _validate_sequence(self, tool_calls: list[dict[str, Any]]) -> dict[str, Any]:
        """호출 순서 검증 (부분 순서 매칭)"""
        if not self.expected_sequence:
            return {"name": "sequence", "passed": True, "message": "순서 검증 없음"}

        called_sequence = [call.get("name", call.get("tool", "")) for call in tool_calls]

        # 부분 순서 매칭: expected_sequence의 순서대로 called_sequence에 존재하는지
        expected_idx = 0
        for tool in called_sequence:
            if expected_idx >= len(self.expected_sequence):
                break
            if tool == self.expected_sequence[expected_idx]:
                expected_idx += 1

        passed = expected_idx == len(self.expected_sequence)
        if passed:
            message = f"호출 순서 일치: {' -> '.join(self.expected_sequence)}"
        else:
            matched = self.expected_sequence[:expected_idx]
            unmatched = self.expected_sequence[expected_idx:]
            message = f"순서 불일치. 매칭: {matched}, 미매칭: {unmatched}"

        return {
            "name": "sequence",
            "passed": passed,
            "matched_count": expected_idx,
            "expected_count": len(self.expected_sequence),
            "message": message,
        }

    def _validate_call_counts(self, tool_calls: list[dict[str, Any]]) -> dict[str, Any]:
        """호출 횟수 검증"""
        # 도구별 호출 횟수 집계
        call_counts: dict[str, int] = {}
        for call in tool_calls:
            tool_name = call.get("name", call.get("tool", ""))
            call_counts[tool_name] = call_counts.get(tool_name, 0) + 1

        violations: list[str] = []

        # 최소 호출 횟수 검증
        for tool, min_count in self.min_calls.items():
            actual = call_counts.get(tool, 0)
            if actual < min_count:
                violations.append(f"{tool}: {actual}/{min_count} (최소)")

        # 최대 호출 횟수 검증
        for tool, max_count in self.max_calls.items():
            actual = call_counts.get(tool, 0)
            if actual > max_count:
                violations.append(f"{tool}: {actual}/{max_count} (최대)")

        passed = len(violations) == 0
        message = "호출 횟수 제한 준수" if passed else f"호출 횟수 위반: {'; '.join(violations)}"

        return {
            "name": "call_counts",
            "passed": passed,
            "violations": violations,
            "counts": call_counts,
            "message": message,
        }

    def _validate_args_patterns(self, tool_calls: list[dict[str, Any]]) -> dict[str, Any]:
        """인자 패턴 검증"""
        violations: list[str] = []

        for tool_name, patterns in self.args_patterns.items():
            # 해당 도구의 모든 호출 검증
            tool_specific_calls = [
                c for c in tool_calls if c.get("name", c.get("tool", "")) == tool_name
            ]

            for i, call in enumerate(tool_specific_calls):
                args = call.get("args", call.get("arguments", {}))
                if isinstance(args, str):
                    try:
                        import json

                        args = json.loads(args)
                    except (json.JSONDecodeError, TypeError):
                        args = {}

                for arg_name, pattern in patterns.items():
                    actual_value = args.get(arg_name)

                    if isinstance(pattern, str):
                        # 문자열 패턴: 정규식 매칭
                        if actual_value is None or not re.match(pattern, str(actual_value)):
                            violations.append(
                                f"{tool_name}[{i}].{arg_name}: '{actual_value}' != '{pattern}'"
                            )
                    elif isinstance(pattern, dict):
                        # 딕셔너리 패턴: 필드별 검증
                        if actual_value != pattern:
                            violations.append(f"{tool_name}[{i}].{arg_name}: 값 불일치")
                    else:
                        # 값 일치 검증
                        if actual_value != pattern:
                            violations.append(
                                f"{tool_name}[{i}].{arg_name}: {actual_value} != {pattern}"
                            )

        passed = len(violations) == 0
        if passed:
            message = "인자 패턴 검증 통과"
        else:
            message = f"인자 패턴 위반: {'; '.join(violations[:3])}"
            if len(violations) > 3:
                message += f" 외 {len(violations) - 3}건"

        return {
            "name": "args_patterns",
            "passed": passed,
            "violations": violations,
            "message": message,
        }

    def _generate_explanation(
        self,
        tool_calls: list[dict[str, Any]],
        validations: list[dict[str, Any]],
    ) -> str:
        """설명 생성"""
        lines = [f"도구 호출 검증 결과 (총 {len(tool_calls)}회 호출):"]

        for validation in validations:
            status = "PASS" if validation["passed"] else "FAIL"
            lines.append(f"  - [{status}] {validation['name']}: {validation['message']}")

        # 호출된 도구 요약
        tool_summary: dict[str, int] = {}
        for call in tool_calls:
            tool_name = call.get("name", call.get("tool", "unknown"))
            tool_summary[tool_name] = tool_summary.get(tool_name, 0) + 1

        if tool_summary:
            summary_str = ", ".join(f"{k}({v})" for k, v in sorted(tool_summary.items()))
            lines.append(f"\n호출된 도구: {summary_str}")

        return "\n".join(lines)

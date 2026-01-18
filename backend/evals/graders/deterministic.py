"""
결정적 채점기 (Deterministic Graders)

테스트 실행, 정적 분석 기반의 결정적 채점기 구현
"""

import asyncio
import json
import re
import time
from pathlib import Path
from typing import Any

import structlog

from backend.evals.graders.base import BaseGrader
from backend.evals.models.entities import GraderResult, Trial
from backend.evals.models.enums import GraderType

logger = structlog.get_logger(__name__)

# 기본 타임아웃 (초)
DEFAULT_TIMEOUT = 120


class PytestGrader(BaseGrader):
    """
    pytest 실행 기반 채점기

    pytest를 실행하여 테스트 통과 여부로 채점
    """

    grader_type: str = GraderType.DETERMINISTIC_TESTS.value

    def __init__(
        self,
        test_paths: list[str],
        pytest_args: list[str] | None = None,
        working_dir: str | None = None,
        timeout_seconds: int = DEFAULT_TIMEOUT,
        fail_fast: bool = False,
        coverage_threshold: float | None = None,
        grader_id: str | None = None,
        weight: float = 1.0,
        required: bool = False,
        description: str | None = None,
    ):
        """
        PytestGrader 초기화

        Args:
            test_paths: 테스트 파일/디렉토리 경로 목록
            pytest_args: pytest 추가 인자
            working_dir: 작업 디렉토리
            timeout_seconds: 테스트 타임아웃
            fail_fast: 첫 실패 시 중단
            coverage_threshold: 커버리지 임계값 (0-100)
            grader_id: 채점기 ID
            weight: 가중치
            required: 필수 통과 여부
            description: 설명
        """
        super().__init__(grader_id, weight, required, description)
        self.test_paths = test_paths
        self.pytest_args = pytest_args or ["-v", "--tb=short"]
        self.working_dir = working_dir
        self.timeout_seconds = timeout_seconds
        self.fail_fast = fail_fast
        self.coverage_threshold = coverage_threshold

    async def grade(self, trial: Trial) -> GraderResult:
        """pytest 실행 및 결과 채점"""
        start_time = time.perf_counter()

        # pytest 명령어 구성
        cmd = ["python", "-m", "pytest"]
        cmd.extend(self.pytest_args)

        if self.fail_fast:
            cmd.append("-x")

        # JSON 출력 포맷 추가
        cmd.append("--json-report")
        cmd.append("--json-report-file=/dev/stdout")

        cmd.extend(self.test_paths)

        logger.info(
            "pytest 실행 시작",
            trial_id=trial.trial_id,
            test_paths=self.test_paths,
            timeout=self.timeout_seconds,
        )

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_dir,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout_seconds,
            )

            duration = time.perf_counter() - start_time
            stdout_text = stdout.decode("utf-8", errors="replace")
            stderr_text = stderr.decode("utf-8", errors="replace")

            # 결과 파싱
            result = self._parse_pytest_output(stdout_text, stderr_text, process.returncode or 0)

            passed = result["passed_tests"] > 0 and result["failed_tests"] == 0
            total = result["passed_tests"] + result["failed_tests"]
            score = result["passed_tests"] / total if total > 0 else 0.0

            partial_scores = {
                "passed_tests": float(result["passed_tests"]),
                "failed_tests": float(result["failed_tests"]),
                "error_tests": float(result["error_tests"]),
                "skipped_tests": float(result["skipped_tests"]),
            }

            explanation = (
                f"테스트 결과: {result['passed_tests']} 통과, "
                f"{result['failed_tests']} 실패, "
                f"{result['error_tests']} 에러, "
                f"{result['skipped_tests']} 스킵"
            )

            if result["failed_tests"] > 0:
                explanation += f"\n실패 상세: {result.get('failure_details', 'N/A')}"

            logger.info(
                "pytest 실행 완료",
                trial_id=trial.trial_id,
                passed=passed,
                score=score,
                duration=duration,
            )

            return self._create_result(
                trial_id=trial.trial_id,
                score=score,
                passed=passed,
                explanation=explanation,
                partial_scores=partial_scores,
                duration_seconds=duration,
            )

        except TimeoutError:
            duration = time.perf_counter() - start_time
            logger.warning(
                "pytest 타임아웃",
                trial_id=trial.trial_id,
                timeout=self.timeout_seconds,
            )
            return self._create_result(
                trial_id=trial.trial_id,
                score=0.0,
                passed=False,
                explanation=f"테스트 타임아웃 ({self.timeout_seconds}초)",
                duration_seconds=duration,
                error_message="TimeoutError",
            )

        except Exception as e:
            duration = time.perf_counter() - start_time
            logger.error(
                "pytest 실행 실패",
                trial_id=trial.trial_id,
                error=str(e),
            )
            return self._create_result(
                trial_id=trial.trial_id,
                score=0.0,
                passed=False,
                explanation=f"테스트 실행 실패: {e}",
                duration_seconds=duration,
                error_message=str(e),
            )

    def _parse_pytest_output(self, stdout: str, stderr: str, return_code: int) -> dict[str, Any]:
        """pytest 출력 파싱"""
        result: dict[str, Any] = {
            "passed_tests": 0,
            "failed_tests": 0,
            "error_tests": 0,
            "skipped_tests": 0,
            "failure_details": "",
        }

        # JSON 리포트 파싱 시도
        try:
            json_match = re.search(r'\{.*"summary".*\}', stdout, re.DOTALL)
            if json_match:
                report = json.loads(json_match.group())
                summary = report.get("summary", {})
                result["passed_tests"] = summary.get("passed", 0)
                result["failed_tests"] = summary.get("failed", 0)
                result["error_tests"] = summary.get("error", 0)
                result["skipped_tests"] = summary.get("skipped", 0)

                # 실패 상세 정보 추출
                tests = report.get("tests", [])
                failures = [t for t in tests if t.get("outcome") == "failed"]
                if failures:
                    failure_details = [
                        f"- {f.get('nodeid', 'unknown')}: {f.get('call', {}).get('longrepr', '')[:200]}"
                        for f in failures[:3]  # 최대 3개
                    ]
                    result["failure_details"] = "\n".join(failure_details)
                return result
        except (json.JSONDecodeError, AttributeError):
            pass

        # 텍스트 출력 파싱 (폴백)
        # pytest 요약 라인: "5 passed, 2 failed in 1.23s"
        summary_pattern = r"(\d+)\s+passed|(\d+)\s+failed|(\d+)\s+error|(\d+)\s+skipped"
        for match in re.finditer(summary_pattern, stdout):
            if match.group(1):
                result["passed_tests"] = int(match.group(1))
            if match.group(2):
                result["failed_tests"] = int(match.group(2))
            if match.group(3):
                result["error_tests"] = int(match.group(3))
            if match.group(4):
                result["skipped_tests"] = int(match.group(4))

        # return code 기반 폴백
        if return_code == 0 and result["passed_tests"] == 0:
            # 최소 1개 통과로 간주
            result["passed_tests"] = 1
        elif return_code != 0 and result["failed_tests"] == 0:
            result["failed_tests"] = 1

        return result


class RuffGrader(BaseGrader):
    """
    ruff 린트 체크 기반 채점기

    ruff를 실행하여 린트 에러 수 기반으로 채점
    """

    grader_type: str = GraderType.STATIC_ANALYSIS.value

    def __init__(
        self,
        target_paths: list[str] | None = None,
        config_file: str | None = None,
        max_errors: int = 0,
        allow_warnings: bool = False,
        timeout_seconds: int = DEFAULT_TIMEOUT,
        grader_id: str | None = None,
        weight: float = 1.0,
        required: bool = False,
        description: str | None = None,
    ):
        """
        RuffGrader 초기화

        Args:
            target_paths: 분석 대상 경로 목록 (기본: 현재 디렉토리)
            config_file: ruff 설정 파일 경로
            max_errors: 허용 에러 개수
            allow_warnings: 경고 허용 여부
            timeout_seconds: 타임아웃
            grader_id: 채점기 ID
            weight: 가중치
            required: 필수 통과 여부
            description: 설명
        """
        super().__init__(grader_id, weight, required, description)
        self.target_paths = target_paths or ["."]
        self.config_file = config_file
        self.max_errors = max_errors
        self.allow_warnings = allow_warnings
        self.timeout_seconds = timeout_seconds

    async def grade(self, trial: Trial) -> GraderResult:
        """ruff check 실행 및 결과 채점"""
        start_time = time.perf_counter()

        # ruff 명령어 구성
        cmd = ["ruff", "check", "--output-format=json"]

        if self.config_file:
            cmd.extend(["--config", self.config_file])

        cmd.extend(self.target_paths)

        logger.info(
            "ruff 린트 체크 시작",
            trial_id=trial.trial_id,
            target_paths=self.target_paths,
        )

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout_seconds,
            )

            duration = time.perf_counter() - start_time
            stdout_text = stdout.decode("utf-8", errors="replace")

            # 결과 파싱
            result = self._parse_ruff_output(stdout_text)

            error_count = result["error_count"]
            warning_count = result["warning_count"]

            # 점수 계산
            if error_count <= self.max_errors:
                passed = True
                # 에러가 적을수록 높은 점수
                if self.max_errors > 0:
                    score = 1.0 - (error_count / (self.max_errors + 1))
                else:
                    score = 1.0 if error_count == 0 else 0.0
            else:
                passed = False
                score = max(0.0, 1.0 - (error_count / (self.max_errors + 10)))

            partial_scores = {
                "error_count": float(error_count),
                "warning_count": float(warning_count),
            }

            explanation = f"ruff 분석 결과: 에러 {error_count}개, 경고 {warning_count}개"
            if result["issues"]:
                issues_summary = ", ".join(result["issues"][:5])
                explanation += f"\n주요 이슈: {issues_summary}"

            logger.info(
                "ruff 린트 체크 완료",
                trial_id=trial.trial_id,
                error_count=error_count,
                passed=passed,
            )

            return self._create_result(
                trial_id=trial.trial_id,
                score=score,
                passed=passed,
                explanation=explanation,
                partial_scores=partial_scores,
                duration_seconds=duration,
            )

        except TimeoutError:
            duration = time.perf_counter() - start_time
            return self._create_result(
                trial_id=trial.trial_id,
                score=0.0,
                passed=False,
                explanation=f"ruff 타임아웃 ({self.timeout_seconds}초)",
                duration_seconds=duration,
                error_message="TimeoutError",
            )

        except Exception as e:
            duration = time.perf_counter() - start_time
            return self._create_result(
                trial_id=trial.trial_id,
                score=0.0,
                passed=False,
                explanation=f"ruff 실행 실패: {e}",
                duration_seconds=duration,
                error_message=str(e),
            )

    def _parse_ruff_output(self, stdout: str) -> dict[str, Any]:
        """ruff JSON 출력 파싱"""
        result: dict[str, Any] = {
            "error_count": 0,
            "warning_count": 0,
            "issues": [],
        }

        try:
            issues = json.loads(stdout)
            if isinstance(issues, list):
                for issue in issues:
                    code = issue.get("code", "")
                    # E로 시작하면 에러, W로 시작하면 경고
                    if code.startswith("E") or code.startswith("F"):
                        result["error_count"] += 1
                    else:
                        result["warning_count"] += 1

                    # 이슈 요약 저장
                    filename = issue.get("filename", "unknown")
                    line = issue.get("location", {}).get("row", 0)
                    message = issue.get("message", "")
                    result["issues"].append(f"{code}:{Path(filename).name}:{line} - {message[:50]}")
        except json.JSONDecodeError:
            # JSON 파싱 실패 시 텍스트 기반 카운트
            result["error_count"] = len(stdout.strip().split("\n")) if stdout.strip() else 0

        return result


class MypyGrader(BaseGrader):
    """
    mypy 타입 체크 기반 채점기

    mypy를 실행하여 타입 에러 수 기반으로 채점
    """

    grader_type: str = GraderType.STATIC_ANALYSIS.value

    def __init__(
        self,
        target_paths: list[str] | None = None,
        config_file: str | None = None,
        max_errors: int = 0,
        strict: bool = False,
        timeout_seconds: int = DEFAULT_TIMEOUT,
        grader_id: str | None = None,
        weight: float = 1.0,
        required: bool = False,
        description: str | None = None,
    ):
        """
        MypyGrader 초기화

        Args:
            target_paths: 분석 대상 경로 목록
            config_file: mypy 설정 파일 경로
            max_errors: 허용 에러 개수
            strict: strict 모드 활성화
            timeout_seconds: 타임아웃
            grader_id: 채점기 ID
            weight: 가중치
            required: 필수 통과 여부
            description: 설명
        """
        super().__init__(grader_id, weight, required, description)
        self.target_paths = target_paths or ["."]
        self.config_file = config_file
        self.max_errors = max_errors
        self.strict = strict
        self.timeout_seconds = timeout_seconds

    async def grade(self, trial: Trial) -> GraderResult:
        """mypy 실행 및 결과 채점"""
        start_time = time.perf_counter()

        # mypy 명령어 구성
        cmd = ["python", "-m", "mypy", "--output=json"]

        if self.config_file:
            cmd.extend(["--config-file", self.config_file])

        if self.strict:
            cmd.append("--strict")

        cmd.extend(self.target_paths)

        logger.info(
            "mypy 타입 체크 시작",
            trial_id=trial.trial_id,
            target_paths=self.target_paths,
        )

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout_seconds,
            )

            duration = time.perf_counter() - start_time
            stdout_text = stdout.decode("utf-8", errors="replace")

            # 결과 파싱
            result = self._parse_mypy_output(stdout_text, process.returncode or 0)

            error_count = result["error_count"]
            warning_count = result["warning_count"]

            # 점수 계산
            if error_count <= self.max_errors:
                passed = True
                if self.max_errors > 0:
                    score = 1.0 - (error_count / (self.max_errors + 1))
                else:
                    score = 1.0 if error_count == 0 else 0.0
            else:
                passed = False
                score = max(0.0, 1.0 - (error_count / (self.max_errors + 10)))

            partial_scores = {
                "error_count": float(error_count),
                "warning_count": float(warning_count),
            }

            explanation = f"mypy 분석 결과: 에러 {error_count}개, 경고 {warning_count}개"
            if result["issues"]:
                issues_summary = ", ".join(result["issues"][:5])
                explanation += f"\n주요 이슈: {issues_summary}"

            logger.info(
                "mypy 타입 체크 완료",
                trial_id=trial.trial_id,
                error_count=error_count,
                passed=passed,
            )

            return self._create_result(
                trial_id=trial.trial_id,
                score=score,
                passed=passed,
                explanation=explanation,
                partial_scores=partial_scores,
                duration_seconds=duration,
            )

        except TimeoutError:
            duration = time.perf_counter() - start_time
            return self._create_result(
                trial_id=trial.trial_id,
                score=0.0,
                passed=False,
                explanation=f"mypy 타임아웃 ({self.timeout_seconds}초)",
                duration_seconds=duration,
                error_message="TimeoutError",
            )

        except Exception as e:
            duration = time.perf_counter() - start_time
            return self._create_result(
                trial_id=trial.trial_id,
                score=0.0,
                passed=False,
                explanation=f"mypy 실행 실패: {e}",
                duration_seconds=duration,
                error_message=str(e),
            )

    def _parse_mypy_output(self, stdout: str, return_code: int) -> dict[str, Any]:
        """mypy 출력 파싱"""
        result: dict[str, Any] = {
            "error_count": 0,
            "warning_count": 0,
            "issues": [],
        }

        # JSON 라인별 파싱 시도
        for line in stdout.strip().split("\n"):
            if not line.strip():
                continue

            try:
                issue = json.loads(line)
                severity = issue.get("severity", "error")
                if severity == "error":
                    result["error_count"] += 1
                else:
                    result["warning_count"] += 1

                # 이슈 요약 저장
                file_path = issue.get("file", "unknown")
                line_num = issue.get("line", 0)
                message = issue.get("message", "")
                result["issues"].append(f"{Path(file_path).name}:{line_num} - {message[:50]}")
            except json.JSONDecodeError:
                # JSON이 아닌 라인 (일반 텍스트 출력)
                if ": error:" in line:
                    result["error_count"] += 1
                    result["issues"].append(line[:100])
                elif ": note:" in line or ": warning:" in line:
                    result["warning_count"] += 1

        # return code 기반 폴백
        if return_code != 0 and result["error_count"] == 0:
            result["error_count"] = 1

        return result

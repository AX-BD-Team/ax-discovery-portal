"""
상태 검증 채점기 (State Check Grader)

환경 상태 검증 기반 채점기 구현
"""

import asyncio
import os
import re
import time
from pathlib import Path
from typing import Any, Literal

import structlog

from backend.evals.graders.base import BaseGrader
from backend.evals.models.entities import GraderResult, Trial
from backend.evals.models.enums import GraderType

logger = structlog.get_logger(__name__)

# 기본 타임아웃 (초)
DEFAULT_TIMEOUT = 60

# 체크 타입 정의
CheckType = Literal[
    "file_exists",
    "file_not_exists",
    "file_content",
    "file_contains",
    "dir_exists",
    "db_row_exists",
    "db_row_value",
    "api_response",
    "api_returns",
    "env_var",
    "process_running",
    "port_listening",
]

# 연산자 정의
Operator = Literal["eq", "ne", "gt", "gte", "lt", "lte", "contains", "matches"]


class StateCheckGrader(BaseGrader):
    """
    환경 상태 검증 채점기

    다양한 상태 체크 항목을 실행하여 통과율 기반으로 채점
    """

    grader_type: str = GraderType.STATE_CHECK.value

    def __init__(
        self,
        checks: list[dict[str, Any]],
        timeout_seconds: int = DEFAULT_TIMEOUT,
        grader_id: str | None = None,
        weight: float = 1.0,
        required: bool = False,
        description: str | None = None,
    ):
        """
        StateCheckGrader 초기화

        Args:
            checks: 체크 항목 목록
                예: [
                    {"type": "db_row_exists", "table": "signals", "where": {"signal_id": "..."}},
                    {"type": "file_contains", "path": "/tmp/output.json", "content": "..."},
                    {"type": "api_returns", "endpoint": "/health", "status": 200}
                ]
            timeout_seconds: 전체 타임아웃
            grader_id: 채점기 ID
            weight: 가중치
            required: 필수 통과 여부
            description: 설명
        """
        super().__init__(grader_id, weight, required, description)
        self.checks = checks
        self.timeout_seconds = timeout_seconds

    async def grade(self, trial: Trial) -> GraderResult:
        """각 체크 실행 후 통과율 계산"""
        start_time = time.perf_counter()

        logger.info(
            "상태 체크 시작",
            trial_id=trial.trial_id,
            check_count=len(self.checks),
        )

        check_results: list[dict[str, Any]] = []
        passed_count = 0
        partial_scores: dict[str, float] = {}

        try:
            for i, check in enumerate(self.checks):
                check_type = check.get("type", "unknown")
                check_id = check.get("id", f"check_{i}")

                try:
                    result = await asyncio.wait_for(
                        self._execute_check(check),
                        timeout=self.timeout_seconds / max(len(self.checks), 1),
                    )

                    if result["passed"]:
                        passed_count += 1
                        partial_scores[check_id] = 1.0
                    else:
                        partial_scores[check_id] = 0.0

                    check_results.append(
                        {
                            "check_id": check_id,
                            "type": check_type,
                            "passed": result["passed"],
                            "message": result.get("message", ""),
                        }
                    )

                except TimeoutError:
                    partial_scores[check_id] = 0.0
                    check_results.append(
                        {
                            "check_id": check_id,
                            "type": check_type,
                            "passed": False,
                            "message": "체크 타임아웃",
                        }
                    )

                except Exception as e:
                    partial_scores[check_id] = 0.0
                    check_results.append(
                        {
                            "check_id": check_id,
                            "type": check_type,
                            "passed": False,
                            "message": f"체크 실패: {e}",
                        }
                    )

            duration = time.perf_counter() - start_time

            # 점수 계산
            total_checks = len(self.checks)
            score = passed_count / total_checks if total_checks > 0 else 0.0
            passed = passed_count == total_checks

            # 설명 생성
            explanation = f"상태 체크: {passed_count}/{total_checks} 통과"
            failed_checks = [r for r in check_results if not r["passed"]]
            if failed_checks:
                failure_details = ", ".join(
                    f"{r['check_id']}({r['type']}): {r['message']}" for r in failed_checks[:3]
                )
                explanation += f"\n실패 항목: {failure_details}"

            logger.info(
                "상태 체크 완료",
                trial_id=trial.trial_id,
                passed_count=passed_count,
                total_checks=total_checks,
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

        except Exception as e:
            duration = time.perf_counter() - start_time
            logger.error(
                "상태 체크 실패",
                trial_id=trial.trial_id,
                error=str(e),
            )
            return self._create_result(
                trial_id=trial.trial_id,
                score=0.0,
                passed=False,
                explanation=f"상태 체크 실패: {e}",
                duration_seconds=duration,
                error_message=str(e),
            )

    async def _execute_check(self, check: dict[str, Any]) -> dict[str, Any]:
        """개별 체크 실행"""
        check_type = check.get("type", "unknown")

        check_handlers = {
            "file_exists": self._check_file_exists,
            "file_not_exists": self._check_file_not_exists,
            "file_content": self._check_file_content,
            "file_contains": self._check_file_contains,
            "dir_exists": self._check_dir_exists,
            "db_row_exists": self._check_db_row_exists,
            "db_row_value": self._check_db_row_value,
            "api_response": self._check_api_response,
            "api_returns": self._check_api_returns,
            "env_var": self._check_env_var,
            "process_running": self._check_process_running,
            "port_listening": self._check_port_listening,
        }

        handler = check_handlers.get(check_type)
        if handler:
            return await handler(check)
        else:
            return {"passed": False, "message": f"알 수 없는 체크 타입: {check_type}"}

    async def _check_file_exists(self, check: dict[str, Any]) -> dict[str, Any]:
        """파일 존재 체크"""
        path = check.get("path") or check.get("target", "")
        exists = Path(path).exists()
        return {
            "passed": exists,
            "message": f"파일 {'존재함' if exists else '없음'}: {path}",
        }

    async def _check_file_not_exists(self, check: dict[str, Any]) -> dict[str, Any]:
        """파일 미존재 체크"""
        path = check.get("path") or check.get("target", "")
        not_exists = not Path(path).exists()
        return {
            "passed": not_exists,
            "message": f"파일 {'없음' if not_exists else '존재함'}: {path}",
        }

    async def _check_file_content(self, check: dict[str, Any]) -> dict[str, Any]:
        """파일 내용 검증"""
        path = check.get("path") or check.get("target", "")
        expected = check.get("expected") or check.get("value", "")
        operator = check.get("operator", "eq")

        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()

            passed = self._compare_values(content, expected, operator)
            return {
                "passed": passed,
                "message": f"파일 내용 {'일치' if passed else '불일치'}: {path}",
            }
        except Exception as e:
            return {"passed": False, "message": f"파일 읽기 실패: {e}"}

    async def _check_file_contains(self, check: dict[str, Any]) -> dict[str, Any]:
        """파일 내용 포함 체크"""
        path = check.get("path") or check.get("target", "")
        content = check.get("content") or check.get("value", "")

        try:
            with open(path, encoding="utf-8") as f:
                file_content = f.read()

            contains = content in file_content
            return {
                "passed": contains,
                "message": f"파일에 내용 {'포함' if contains else '미포함'}: {path}",
            }
        except Exception as e:
            return {"passed": False, "message": f"파일 읽기 실패: {e}"}

    async def _check_dir_exists(self, check: dict[str, Any]) -> dict[str, Any]:
        """디렉토리 존재 체크"""
        path = check.get("path") or check.get("target", "")
        exists = Path(path).is_dir()
        return {
            "passed": exists,
            "message": f"디렉토리 {'존재함' if exists else '없음'}: {path}",
        }

    async def _check_db_row_exists(self, check: dict[str, Any]) -> dict[str, Any]:
        """DB 행 존재 체크 (TODO: 실제 DB 연결 구현 필요)"""
        table = check.get("table", "")
        where = check.get("where", {})
        # 실제 구현에서는 DB 쿼리 실행
        logger.warning("DB 체크는 아직 구현되지 않음", table=table, where=where)
        return {
            "passed": False,
            "message": f"DB 체크 미구현: {table}",
        }

    async def _check_db_row_value(self, check: dict[str, Any]) -> dict[str, Any]:
        """DB 행 값 체크 (TODO: 실제 DB 연결 구현 필요)"""
        table = check.get("table", "")
        _where = check.get("where", {})  # noqa: F841 향후 사용 예정
        _expected = check.get("expected", {})  # noqa: F841 향후 사용 예정
        logger.warning("DB 체크는 아직 구현되지 않음", table=table)
        return {
            "passed": False,
            "message": f"DB 체크 미구현: {table}",
        }

    async def _check_api_response(self, check: dict[str, Any]) -> dict[str, Any]:
        """API 응답 체크"""
        return await self._check_api_returns(check)

    async def _check_api_returns(self, check: dict[str, Any]) -> dict[str, Any]:
        """API 응답 체크"""
        endpoint = check.get("endpoint", "")
        expected_status = check.get("status", 200)
        method = check.get("method", "GET")
        timeout = check.get("timeout", 10)

        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method, endpoint, timeout=aiohttp.ClientTimeout(total=timeout)
                ) as resp:
                    actual_status = resp.status
                    passed = actual_status == expected_status
                    return {
                        "passed": passed,
                        "message": f"API 응답: {actual_status} (기대: {expected_status})",
                    }
        except ImportError:
            # aiohttp 없을 경우 curl 사용
            cmd = ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", endpoint]
            try:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await asyncio.wait_for(process.communicate(), timeout=timeout)
                actual_status = int(stdout.decode().strip())
                passed = actual_status == expected_status
                return {
                    "passed": passed,
                    "message": f"API 응답: {actual_status} (기대: {expected_status})",
                }
            except Exception as e:
                return {"passed": False, "message": f"API 체크 실패: {e}"}
        except Exception as e:
            return {"passed": False, "message": f"API 체크 실패: {e}"}

    async def _check_env_var(self, check: dict[str, Any]) -> dict[str, Any]:
        """환경 변수 체크"""
        var_name = check.get("target", "") or check.get("name", "")
        expected = check.get("expected") or check.get("value")
        operator = check.get("operator", "eq")

        actual = os.environ.get(var_name)

        if expected is None:
            # 존재 여부만 체크
            passed = actual is not None
            return {
                "passed": passed,
                "message": f"환경변수 {'존재함' if passed else '없음'}: {var_name}",
            }
        else:
            passed = self._compare_values(actual, expected, operator)
            return {
                "passed": passed,
                "message": f"환경변수 {var_name}: {actual} (기대: {expected})",
            }

    async def _check_process_running(self, check: dict[str, Any]) -> dict[str, Any]:
        """프로세스 실행 체크"""
        process_name = check.get("target", "") or check.get("name", "")

        try:
            cmd = ["pgrep", "-f", process_name]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await process.communicate()
            running = bool(stdout.strip())
            return {
                "passed": running,
                "message": f"프로세스 {'실행 중' if running else '실행 안함'}: {process_name}",
            }
        except Exception as e:
            return {"passed": False, "message": f"프로세스 체크 실패: {e}"}

    async def _check_port_listening(self, check: dict[str, Any]) -> dict[str, Any]:
        """포트 리스닝 체크"""
        port = check.get("target") or check.get("port", 0)
        host = check.get("host", "localhost")

        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host, int(port)),
                timeout=5,
            )
            writer.close()
            await writer.wait_closed()
            return {
                "passed": True,
                "message": f"포트 {port} 리스닝 중",
            }
        except (TimeoutError, ConnectionRefusedError, OSError):
            return {
                "passed": False,
                "message": f"포트 {port} 리스닝 안함",
            }
        except Exception as e:
            return {"passed": False, "message": f"포트 체크 실패: {e}"}

    def _compare_values(self, actual: Any, expected: Any, operator: str = "eq") -> bool:
        """값 비교"""
        try:
            if operator == "eq":
                return actual == expected
            elif operator == "ne":
                return actual != expected
            elif operator == "gt":
                return float(actual) > float(expected)
            elif operator == "gte":
                return float(actual) >= float(expected)
            elif operator == "lt":
                return float(actual) < float(expected)
            elif operator == "lte":
                return float(actual) <= float(expected)
            elif operator == "contains":
                return str(expected) in str(actual)
            elif operator == "matches":
                return bool(re.match(str(expected), str(actual)))
            else:
                return actual == expected
        except (TypeError, ValueError):
            return False

"""
Cloudflare D1 HTTP API Client

D1 REST API를 통해 SQLite 데이터베이스와 통신합니다.
https://developers.cloudflare.com/api/operations/cloudflare-d1-query-database
"""

import os
from typing import Any

import httpx
import structlog

logger = structlog.get_logger()


class D1Client:
    """Cloudflare D1 HTTP API 클라이언트"""

    def __init__(self) -> None:
        self.account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
        self.database_id = os.getenv("D1_DATABASE_ID", "")
        self.api_token = os.getenv("CLOUDFLARE_API_TOKEN", "")

        self._validate_config()

    def _validate_config(self) -> None:
        """설정 유효성 검사"""
        missing = []
        if not self.account_id:
            missing.append("CLOUDFLARE_ACCOUNT_ID")
        if not self.database_id:
            missing.append("D1_DATABASE_ID")
        if not self.api_token:
            missing.append("CLOUDFLARE_API_TOKEN")

        if missing:
            logger.warning(
                "D1 클라이언트 설정 누락",
                missing_vars=missing,
                message="D1 기능이 비활성화됩니다",
            )

    @property
    def base_url(self) -> str:
        """D1 API 기본 URL"""
        return (
            f"https://api.cloudflare.com/client/v4/accounts/"
            f"{self.account_id}/d1/database/{self.database_id}"
        )

    @property
    def headers(self) -> dict[str, str]:
        """API 요청 헤더"""
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

    @property
    def is_configured(self) -> bool:
        """D1 클라이언트가 설정되었는지 확인"""
        return bool(self.account_id and self.database_id and self.api_token)

    async def execute(
        self,
        sql: str,
        params: list[Any] | None = None,
    ) -> dict[str, Any]:
        """
        SQL 쿼리 실행

        Args:
            sql: 실행할 SQL 쿼리
            params: 쿼리 파라미터 (? 플레이스홀더)

        Returns:
            쿼리 결과 딕셔너리

        Example:
            result = await d1_client.execute(
                "SELECT * FROM signals WHERE id = ?",
                ["sig_abc123"]
            )
        """
        if not self.is_configured:
            raise RuntimeError("D1 클라이언트가 설정되지 않았습니다")

        logger.debug("D1 쿼리 실행", sql=sql[:100], params_count=len(params or []))

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/query",
                headers=self.headers,
                json={"sql": sql, "params": params or []},
            )

            if response.status_code != 200:
                logger.error(
                    "D1 API 오류",
                    status_code=response.status_code,
                    response=response.text[:500],
                )
                response.raise_for_status()

            result = response.json()

            if not result.get("success"):
                errors = result.get("errors", [])
                logger.error("D1 쿼리 실패", errors=errors)
                raise RuntimeError(f"D1 query failed: {errors}")

            # 결과 반환 (첫 번째 결과 세트)
            results = result.get("result", [])
            if results:
                return results[0]
            return {"results": [], "meta": {}}

    async def execute_batch(
        self,
        statements: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        배치 SQL 쿼리 실행

        Args:
            statements: SQL 문 리스트 [{"sql": "...", "params": [...]}]

        Returns:
            각 쿼리의 결과 리스트
        """
        if not self.is_configured:
            raise RuntimeError("D1 클라이언트가 설정되지 않았습니다")

        logger.debug("D1 배치 쿼리 실행", statement_count=len(statements))

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/query",
                headers=self.headers,
                json=statements,
            )

            response.raise_for_status()
            result = response.json()

            if not result.get("success"):
                raise RuntimeError(f"D1 batch query failed: {result.get('errors')}")

            return result.get("result", [])

    async def health_check(self) -> bool:
        """
        D1 연결 상태 확인

        Returns:
            연결 성공 여부
        """
        if not self.is_configured:
            return False

        try:
            result = await self.execute("SELECT 1 as health")
            return bool(result.get("results"))
        except Exception as e:
            logger.error("D1 헬스체크 실패", error=str(e))
            return False


# 싱글톤 인스턴스
d1_client = D1Client()

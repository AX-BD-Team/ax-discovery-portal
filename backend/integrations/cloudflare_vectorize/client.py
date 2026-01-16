"""
Cloudflare Vectorize HTTP API Client

Vectorize REST API를 통해 벡터 검색을 수행합니다.
https://developers.cloudflare.com/vectorize/reference/client-api/
"""

import os
from typing import Any

import httpx
import structlog

logger = structlog.get_logger()


class VectorMetadata:
    """벡터 메타데이터 구조"""

    def __init__(
        self,
        entity_type: str,
        name: str,
        confidence: float = 1.0,
        external_ref_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        self.entity_type = entity_type
        self.name = name
        self.confidence = confidence
        self.external_ref_id = external_ref_id
        self.extra = kwargs

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환"""
        result = {
            "entity_type": self.entity_type,
            "name": self.name,
            "confidence": self.confidence,
        }
        if self.external_ref_id:
            result["external_ref_id"] = self.external_ref_id
        result.update(self.extra)
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VectorMetadata":
        """딕셔너리에서 생성"""
        return cls(
            entity_type=data.get("entity_type", ""),
            name=data.get("name", ""),
            confidence=data.get("confidence", 1.0),
            external_ref_id=data.get("external_ref_id"),
            **{
                k: v
                for k, v in data.items()
                if k not in ["entity_type", "name", "confidence", "external_ref_id"]
            },
        )


class VectorMatch:
    """벡터 검색 결과"""

    def __init__(
        self,
        id: str,
        score: float,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.id = id
        self.score = score
        self.metadata = VectorMetadata.from_dict(metadata) if metadata else None

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "id": self.id,
            "score": self.score,
            "metadata": self.metadata.to_dict() if self.metadata else None,
        }


class VectorizeClient:
    """
    Cloudflare Vectorize HTTP API 클라이언트

    벡터 데이터의 저장, 검색, 삭제 기능을 제공합니다.
    """

    def __init__(
        self,
        index_name: str | None = None,
        account_id: str | None = None,
        api_token: str | None = None,
    ) -> None:
        """
        Args:
            index_name: Vectorize 인덱스 이름 (미지정 시 환경변수 사용)
            account_id: Cloudflare 계정 ID
            api_token: Cloudflare API 토큰
        """
        self.account_id = account_id or os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
        self.index_name = index_name or os.getenv("VECTORIZE_INDEX_NAME", "ax-discovery-entities")
        self.api_token = api_token or os.getenv("CLOUDFLARE_API_TOKEN", "")

        self._validate_config()

    def _validate_config(self) -> None:
        """설정 유효성 검사"""
        missing = []
        if not self.account_id:
            missing.append("CLOUDFLARE_ACCOUNT_ID")
        if not self.api_token:
            missing.append("CLOUDFLARE_API_TOKEN")

        if missing:
            logger.warning(
                "Vectorize 클라이언트 설정 누락",
                missing_vars=missing,
                message="Vectorize 기능이 비활성화됩니다",
            )

    @property
    def is_configured(self) -> bool:
        """클라이언트가 설정되었는지 확인"""
        return bool(self.account_id and self.api_token and self.index_name)

    @property
    def base_url(self) -> str:
        """Vectorize API 기본 URL"""
        return (
            f"https://api.cloudflare.com/client/v4/accounts/"
            f"{self.account_id}/vectorize/v2/indexes/{self.index_name}"
        )

    @property
    def headers(self) -> dict[str, str]:
        """API 요청 헤더"""
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

    async def upsert(
        self,
        vectors: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        벡터 삽입/업데이트

        Args:
            vectors: 벡터 리스트
                [{"id": "ENT-123", "values": [0.1, 0.2, ...], "metadata": {...}}]

        Returns:
            API 응답 결과

        Example:
            await vectorize.upsert([
                {
                    "id": "SIG-001",
                    "values": [0.1, 0.2, ...],  # 1536차원
                    "metadata": {
                        "entity_type": "Signal",
                        "name": "고객 데이터 분석 기회",
                        "confidence": 0.95
                    }
                }
            ])
        """
        if not self.is_configured:
            raise RuntimeError("Vectorize 클라이언트가 설정되지 않았습니다")

        if not vectors:
            return {"mutationId": None, "count": 0}

        logger.debug(
            "Vectorize upsert 요청",
            index=self.index_name,
            vector_count=len(vectors),
        )

        # NDJSON 형식으로 변환 (Vectorize API 요구사항)
        ndjson_lines = []
        for v in vectors:
            ndjson_lines.append(
                {
                    "id": v["id"],
                    "values": v["values"],
                    "metadata": v.get("metadata", {}),
                }
            )

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/upsert",
                headers=self.headers,
                json={"vectors": ndjson_lines},
            )

            if response.status_code not in (200, 201):
                logger.error(
                    "Vectorize upsert 오류",
                    status_code=response.status_code,
                    response=response.text[:500],
                )
                response.raise_for_status()

            result = response.json()

            if not result.get("success"):
                errors = result.get("errors", [])
                logger.error("Vectorize upsert 실패", errors=errors)
                raise RuntimeError(f"Vectorize upsert 실패: {errors}")

            logger.info(
                "Vectorize upsert 완료",
                mutation_id=result.get("result", {}).get("mutationId"),
                count=len(vectors),
            )

            return result.get("result", {})

    async def query(
        self,
        vector: list[float],
        top_k: int = 10,
        filter: dict[str, Any] | None = None,
        return_values: bool = False,
        return_metadata: bool = True,
    ) -> list[VectorMatch]:
        """
        벡터 유사도 검색

        Args:
            vector: 쿼리 벡터 (임베딩)
            top_k: 반환할 결과 수 (최대 100)
            filter: 메타데이터 필터
                예: {"entity_type": {"$eq": "Signal"}}
                예: {"confidence": {"$gte": 0.8}}
            return_values: 벡터 값 반환 여부
            return_metadata: 메타데이터 반환 여부

        Returns:
            VectorMatch 리스트 (score 내림차순)

        Example:
            matches = await vectorize.query(
                vector=[0.1, 0.2, ...],
                top_k=10,
                filter={"entity_type": {"$eq": "Signal"}}
            )
        """
        if not self.is_configured:
            raise RuntimeError("Vectorize 클라이언트가 설정되지 않았습니다")

        logger.debug(
            "Vectorize query 요청",
            index=self.index_name,
            top_k=top_k,
            has_filter=filter is not None,
        )

        payload: dict[str, Any] = {
            "vector": vector,
            "topK": min(top_k, 100),
            "returnValues": return_values,
            "returnMetadata": "all" if return_metadata else "none",
        }

        if filter:
            payload["filter"] = filter

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/query",
                headers=self.headers,
                json=payload,
            )

            if response.status_code != 200:
                logger.error(
                    "Vectorize query 오류",
                    status_code=response.status_code,
                    response=response.text[:500],
                )
                response.raise_for_status()

            result = response.json()

            if not result.get("success"):
                errors = result.get("errors", [])
                logger.error("Vectorize query 실패", errors=errors)
                raise RuntimeError(f"Vectorize query 실패: {errors}")

            matches_data = result.get("result", {}).get("matches", [])

            matches = [
                VectorMatch(
                    id=m["id"],
                    score=m.get("score", 0.0),
                    metadata=m.get("metadata"),
                )
                for m in matches_data
            ]

            logger.debug(
                "Vectorize query 완료",
                match_count=len(matches),
            )

            return matches

    async def get_by_ids(
        self,
        ids: list[str],
    ) -> list[dict[str, Any]]:
        """
        ID로 벡터 조회

        Args:
            ids: 조회할 벡터 ID 리스트

        Returns:
            벡터 데이터 리스트
        """
        if not self.is_configured:
            raise RuntimeError("Vectorize 클라이언트가 설정되지 않았습니다")

        if not ids:
            return []

        logger.debug(
            "Vectorize get_by_ids 요청",
            index=self.index_name,
            id_count=len(ids),
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/getByIds",
                headers=self.headers,
                json={"ids": ids},
            )

            if response.status_code != 200:
                logger.error(
                    "Vectorize get_by_ids 오류",
                    status_code=response.status_code,
                    response=response.text[:500],
                )
                response.raise_for_status()

            result = response.json()

            if not result.get("success"):
                raise RuntimeError(f"Vectorize get_by_ids 실패: {result.get('errors')}")

            return result.get("result", {}).get("vectors", [])

    async def delete(
        self,
        ids: list[str],
    ) -> dict[str, Any]:
        """
        벡터 삭제

        Args:
            ids: 삭제할 벡터 ID 리스트

        Returns:
            삭제 결과
        """
        if not self.is_configured:
            raise RuntimeError("Vectorize 클라이언트가 설정되지 않았습니다")

        if not ids:
            return {"mutationId": None, "count": 0}

        logger.debug(
            "Vectorize delete 요청",
            index=self.index_name,
            id_count=len(ids),
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/deleteByIds",
                headers=self.headers,
                json={"ids": ids},
            )

            if response.status_code != 200:
                logger.error(
                    "Vectorize delete 오류",
                    status_code=response.status_code,
                    response=response.text[:500],
                )
                response.raise_for_status()

            result = response.json()

            if not result.get("success"):
                raise RuntimeError(f"Vectorize delete 실패: {result.get('errors')}")

            logger.info(
                "Vectorize delete 완료",
                mutation_id=result.get("result", {}).get("mutationId"),
                count=len(ids),
            )

            return result.get("result", {})

    async def info(self) -> dict[str, Any]:
        """
        인덱스 정보 조회

        Returns:
            인덱스 설정 및 통계 정보
        """
        if not self.is_configured:
            raise RuntimeError("Vectorize 클라이언트가 설정되지 않았습니다")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}",
                headers=self.headers,
            )

            if response.status_code != 200:
                response.raise_for_status()

            result = response.json()

            if not result.get("success"):
                raise RuntimeError(f"Vectorize info 실패: {result.get('errors')}")

            return result.get("result", {})

    async def health_check(self) -> bool:
        """
        Vectorize 연결 상태 확인

        Returns:
            연결 성공 여부
        """
        if not self.is_configured:
            return False

        try:
            info = await self.info()
            return bool(info.get("name"))
        except Exception as e:
            logger.error("Vectorize 헬스체크 실패", error=str(e))
            return False


# 싱글톤 인스턴스
vectorize_client = VectorizeClient()

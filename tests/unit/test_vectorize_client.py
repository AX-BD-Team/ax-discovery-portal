"""
Cloudflare Vectorize Client 테스트
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.integrations.cloudflare_vectorize.client import (
    VectorizeClient,
    VectorMatch,
    VectorMetadata,
)


class TestVectorMetadata:
    """VectorMetadata 테스트"""

    def test_to_dict(self):
        """딕셔너리 변환"""
        metadata = VectorMetadata(
            entity_type="Signal",
            name="테스트 신호",
            confidence=0.95,
            external_ref_id="SIG-001",
            custom_field="custom_value",
        )

        result = metadata.to_dict()

        assert result["entity_type"] == "Signal"
        assert result["name"] == "테스트 신호"
        assert result["confidence"] == 0.95
        assert result["external_ref_id"] == "SIG-001"
        assert result["custom_field"] == "custom_value"

    def test_from_dict(self):
        """딕셔너리에서 생성"""
        data = {
            "entity_type": "Signal",
            "name": "테스트 신호",
            "confidence": 0.9,
            "external_ref_id": "SIG-002",
        }

        metadata = VectorMetadata.from_dict(data)

        assert metadata.entity_type == "Signal"
        assert metadata.name == "테스트 신호"
        assert metadata.confidence == 0.9
        assert metadata.external_ref_id == "SIG-002"


class TestVectorMatch:
    """VectorMatch 테스트"""

    def test_to_dict_with_metadata(self):
        """메타데이터 포함 딕셔너리 변환"""
        match = VectorMatch(
            id="SIG-001",
            score=0.95,
            metadata={"entity_type": "Signal", "name": "테스트"},
        )

        result = match.to_dict()

        assert result["id"] == "SIG-001"
        assert result["score"] == 0.95
        assert result["metadata"]["entity_type"] == "Signal"

    def test_to_dict_without_metadata(self):
        """메타데이터 없이 딕셔너리 변환"""
        match = VectorMatch(id="SIG-001", score=0.8)

        result = match.to_dict()

        assert result["id"] == "SIG-001"
        assert result["score"] == 0.8
        assert result["metadata"] is None


class TestVectorizeClient:
    """VectorizeClient 테스트"""

    def test_init_with_env_vars(self):
        """환경변수로 초기화"""
        env_vars = {
            "CLOUDFLARE_ACCOUNT_ID": "test-account",
            "CLOUDFLARE_API_TOKEN": "test-token",
            "VECTORIZE_INDEX_NAME": "test-index",
        }

        with patch.dict("os.environ", env_vars):
            client = VectorizeClient()

        assert client.account_id == "test-account"
        assert client.api_token == "test-token"
        assert client.index_name == "test-index"
        assert client.is_configured is True

    def test_init_with_explicit_params(self):
        """명시적 파라미터로 초기화"""
        client = VectorizeClient(
            account_id="explicit-account",
            api_token="explicit-token",
            index_name="explicit-index",
        )

        assert client.account_id == "explicit-account"
        assert client.api_token == "explicit-token"
        assert client.index_name == "explicit-index"

    def test_is_configured_without_credentials(self):
        """인증 정보 없이 초기화"""
        with patch.dict("os.environ", {}, clear=True):
            client = VectorizeClient(
                account_id="",
                api_token="",
                index_name="test",
            )

        assert client.is_configured is False

    def test_base_url(self):
        """기본 URL 생성"""
        client = VectorizeClient(
            account_id="acc123",
            api_token="token",
            index_name="my-index",
        )

        expected = (
            "https://api.cloudflare.com/client/v4/accounts/acc123/vectorize/v2/indexes/my-index"
        )
        assert client.base_url == expected

    def test_headers(self):
        """요청 헤더 생성"""
        client = VectorizeClient(
            account_id="acc",
            api_token="my-token",
            index_name="idx",
        )

        headers = client.headers

        assert headers["Authorization"] == "Bearer my-token"
        assert headers["Content-Type"] == "application/json"

    @pytest.mark.asyncio
    async def test_upsert_success(self):
        """벡터 upsert 성공"""
        client = VectorizeClient(
            account_id="acc",
            api_token="token",
            index_name="idx",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "result": {"mutationId": "mut-123"},
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            result = await client.upsert(
                [
                    {
                        "id": "SIG-001",
                        "values": [0.1] * 1536,
                        "metadata": {"entity_type": "Signal"},
                    }
                ]
            )

        assert result["mutationId"] == "mut-123"

    @pytest.mark.asyncio
    async def test_upsert_empty_vectors(self):
        """빈 벡터 리스트 upsert"""
        client = VectorizeClient(
            account_id="acc",
            api_token="token",
            index_name="idx",
        )

        result = await client.upsert([])

        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_upsert_not_configured(self):
        """미설정 시 upsert 오류"""
        with patch.dict("os.environ", {}, clear=True):
            client = VectorizeClient(
                account_id="",
                api_token="",
                index_name="idx",
            )

            with pytest.raises(RuntimeError, match="설정되지 않았습니다"):
                await client.upsert([{"id": "test", "values": [0.1]}])

    @pytest.mark.asyncio
    async def test_query_success(self):
        """벡터 검색 성공"""
        client = VectorizeClient(
            account_id="acc",
            api_token="token",
            index_name="idx",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "result": {
                "matches": [
                    {
                        "id": "SIG-001",
                        "score": 0.95,
                        "metadata": {"entity_type": "Signal", "name": "테스트"},
                    },
                    {
                        "id": "SIG-002",
                        "score": 0.85,
                        "metadata": {"entity_type": "Signal", "name": "테스트2"},
                    },
                ]
            },
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            matches = await client.query(
                vector=[0.1] * 1536,
                top_k=10,
            )

        assert len(matches) == 2
        assert matches[0].id == "SIG-001"
        assert matches[0].score == 0.95
        assert matches[0].metadata.entity_type == "Signal"

    @pytest.mark.asyncio
    async def test_query_with_filter(self):
        """필터 적용 벡터 검색"""
        client = VectorizeClient(
            account_id="acc",
            api_token="token",
            index_name="idx",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "result": {"matches": []},
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post

            await client.query(
                vector=[0.1] * 1536,
                top_k=5,
                filter={"entity_type": {"$eq": "Signal"}},
            )

            # 필터가 포함된 요청 확인
            call_args = mock_post.call_args
            request_json = call_args.kwargs["json"]
            assert "filter" in request_json
            assert request_json["filter"]["entity_type"]["$eq"] == "Signal"

    @pytest.mark.asyncio
    async def test_query_not_configured(self):
        """미설정 시 query 오류"""
        with patch.dict("os.environ", {}, clear=True):
            client = VectorizeClient(
                account_id="",
                api_token="",
                index_name="idx",
            )

            with pytest.raises(RuntimeError, match="설정되지 않았습니다"):
                await client.query(vector=[0.1])

    @pytest.mark.asyncio
    async def test_delete_success(self):
        """벡터 삭제 성공"""
        client = VectorizeClient(
            account_id="acc",
            api_token="token",
            index_name="idx",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "result": {"mutationId": "mut-456"},
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            result = await client.delete(["SIG-001", "SIG-002"])

        assert result["mutationId"] == "mut-456"

    @pytest.mark.asyncio
    async def test_delete_empty_ids(self):
        """빈 ID 리스트 삭제"""
        client = VectorizeClient(
            account_id="acc",
            api_token="token",
            index_name="idx",
        )

        result = await client.delete([])

        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_get_by_ids_success(self):
        """ID로 벡터 조회 성공"""
        client = VectorizeClient(
            account_id="acc",
            api_token="token",
            index_name="idx",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "result": {
                "vectors": [
                    {"id": "SIG-001", "values": [0.1] * 1536},
                ]
            },
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            result = await client.get_by_ids(["SIG-001"])

        assert len(result) == 1
        assert result[0]["id"] == "SIG-001"

    @pytest.mark.asyncio
    async def test_get_by_ids_empty(self):
        """빈 ID 리스트 조회"""
        client = VectorizeClient(
            account_id="acc",
            api_token="token",
            index_name="idx",
        )

        result = await client.get_by_ids([])

        assert result == []

    @pytest.mark.asyncio
    async def test_info_success(self):
        """인덱스 정보 조회 성공"""
        client = VectorizeClient(
            account_id="acc",
            api_token="token",
            index_name="idx",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "result": {
                "name": "idx",
                "dimensions": 1536,
                "metric": "cosine",
            },
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            info = await client.info()

        assert info["name"] == "idx"
        assert info["dimensions"] == 1536

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """헬스체크 성공"""
        client = VectorizeClient(
            account_id="acc",
            api_token="token",
            index_name="idx",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "result": {"name": "idx"},
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            is_healthy = await client.health_check()

        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_not_configured(self):
        """미설정 시 헬스체크 실패"""
        client = VectorizeClient(
            account_id="",
            api_token="",
            index_name="idx",
        )

        is_healthy = await client.health_check()

        assert is_healthy is False

    @pytest.mark.asyncio
    async def test_health_check_error(self):
        """API 오류 시 헬스체크 실패"""
        client = VectorizeClient(
            account_id="acc",
            api_token="token",
            index_name="idx",
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=Exception("Connection failed")
            )

            is_healthy = await client.health_check()

        assert is_healthy is False

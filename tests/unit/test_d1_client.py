"""
Cloudflare D1 Client 단위 테스트
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.integrations.cloudflare_d1.client import D1Client


class TestD1Client:
    """D1Client 테스트"""

    def test_init_without_env_vars(self):
        """환경변수 없이 초기화"""
        with patch.dict("os.environ", {}, clear=True):
            client = D1Client()

            assert client.account_id == ""
            assert client.database_id == ""
            assert client.api_token == ""
            assert client.is_configured is False

    def test_init_with_env_vars(self):
        """환경변수로 초기화"""
        env_vars = {
            "CLOUDFLARE_ACCOUNT_ID": "test_account",
            "D1_DATABASE_ID": "test_db",
            "CLOUDFLARE_API_TOKEN": "test_token",
        }
        with patch.dict("os.environ", env_vars, clear=True):
            client = D1Client()

            assert client.account_id == "test_account"
            assert client.database_id == "test_db"
            assert client.api_token == "test_token"
            assert client.is_configured is True

    def test_base_url(self):
        """기본 URL 확인"""
        env_vars = {
            "CLOUDFLARE_ACCOUNT_ID": "acc123",
            "D1_DATABASE_ID": "db456",
            "CLOUDFLARE_API_TOKEN": "token",
        }
        with patch.dict("os.environ", env_vars, clear=True):
            client = D1Client()

            expected = "https://api.cloudflare.com/client/v4/accounts/acc123/d1/database/db456"
            assert client.base_url == expected

    def test_headers(self):
        """헤더 확인"""
        env_vars = {
            "CLOUDFLARE_ACCOUNT_ID": "acc",
            "D1_DATABASE_ID": "db",
            "CLOUDFLARE_API_TOKEN": "my_token",
        }
        with patch.dict("os.environ", env_vars, clear=True):
            client = D1Client()

            assert client.headers["Authorization"] == "Bearer my_token"
            assert client.headers["Content-Type"] == "application/json"

    def test_is_configured_partial(self):
        """일부 설정만 있을 때"""
        env_vars = {
            "CLOUDFLARE_ACCOUNT_ID": "acc",
            "D1_DATABASE_ID": "",
            "CLOUDFLARE_API_TOKEN": "token",
        }
        with patch.dict("os.environ", env_vars, clear=True):
            client = D1Client()

            assert client.is_configured is False

    @pytest.mark.asyncio
    async def test_execute_not_configured(self):
        """미설정 상태에서 실행 시 오류"""
        with patch.dict("os.environ", {}, clear=True):
            client = D1Client()

            with pytest.raises(RuntimeError, match="D1 클라이언트가 설정되지 않았습니다"):
                await client.execute("SELECT 1")

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """쿼리 실행 성공"""
        env_vars = {
            "CLOUDFLARE_ACCOUNT_ID": "acc",
            "D1_DATABASE_ID": "db",
            "CLOUDFLARE_API_TOKEN": "token",
        }
        with patch.dict("os.environ", env_vars, clear=True):
            client = D1Client()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "success": True,
                "result": [{"results": [{"id": 1}], "meta": {}}],
            }

            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

                result = await client.execute("SELECT * FROM test")

                assert result["results"] == [{"id": 1}]

    @pytest.mark.asyncio
    async def test_execute_with_params(self):
        """파라미터가 있는 쿼리 실행"""
        env_vars = {
            "CLOUDFLARE_ACCOUNT_ID": "acc",
            "D1_DATABASE_ID": "db",
            "CLOUDFLARE_API_TOKEN": "token",
        }
        with patch.dict("os.environ", env_vars, clear=True):
            client = D1Client()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "success": True,
                "result": [{"results": [], "meta": {}}],
            }

            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

                await client.execute("SELECT * FROM test WHERE id = ?", ["test_id"])

                # post가 호출되었는지 확인
                mock_client.post.assert_called_once()
                call_args = mock_client.post.call_args
                assert call_args[1]["json"]["sql"] == "SELECT * FROM test WHERE id = ?"
                assert call_args[1]["json"]["params"] == ["test_id"]

    @pytest.mark.asyncio
    async def test_execute_api_error(self):
        """API 오류 응답"""
        env_vars = {
            "CLOUDFLARE_ACCOUNT_ID": "acc",
            "D1_DATABASE_ID": "db",
            "CLOUDFLARE_API_TOKEN": "token",
        }
        with patch.dict("os.environ", env_vars, clear=True):
            client = D1Client()

            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_response.raise_for_status.side_effect = Exception("HTTP 500")

            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

                with pytest.raises(Exception):
                    await client.execute("SELECT 1")

    @pytest.mark.asyncio
    async def test_execute_query_failure(self):
        """쿼리 실패"""
        env_vars = {
            "CLOUDFLARE_ACCOUNT_ID": "acc",
            "D1_DATABASE_ID": "db",
            "CLOUDFLARE_API_TOKEN": "token",
        }
        with patch.dict("os.environ", env_vars, clear=True):
            client = D1Client()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "success": False,
                "errors": [{"message": "SQL syntax error"}],
            }

            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

                with pytest.raises(RuntimeError, match="D1 query failed"):
                    await client.execute("INVALID SQL")

    @pytest.mark.asyncio
    async def test_execute_empty_result(self):
        """빈 결과"""
        env_vars = {
            "CLOUDFLARE_ACCOUNT_ID": "acc",
            "D1_DATABASE_ID": "db",
            "CLOUDFLARE_API_TOKEN": "token",
        }
        with patch.dict("os.environ", env_vars, clear=True):
            client = D1Client()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "success": True,
                "result": [],
            }

            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

                result = await client.execute("SELECT * FROM empty_table")

                assert result == {"results": [], "meta": {}}

    @pytest.mark.asyncio
    async def test_execute_batch_not_configured(self):
        """미설정 상태에서 배치 실행 시 오류"""
        with patch.dict("os.environ", {}, clear=True):
            client = D1Client()

            with pytest.raises(RuntimeError, match="D1 클라이언트가 설정되지 않았습니다"):
                await client.execute_batch([{"sql": "SELECT 1"}])

    @pytest.mark.asyncio
    async def test_execute_batch_success(self):
        """배치 쿼리 실행 성공"""
        env_vars = {
            "CLOUDFLARE_ACCOUNT_ID": "acc",
            "D1_DATABASE_ID": "db",
            "CLOUDFLARE_API_TOKEN": "token",
        }
        with patch.dict("os.environ", env_vars, clear=True):
            client = D1Client()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "success": True,
                "result": [
                    {"results": [{"id": 1}]},
                    {"results": [{"id": 2}]},
                ],
            }
            mock_response.raise_for_status = MagicMock()

            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

                statements = [
                    {"sql": "SELECT 1", "params": []},
                    {"sql": "SELECT 2", "params": []},
                ]
                result = await client.execute_batch(statements)

                assert len(result) == 2

    @pytest.mark.asyncio
    async def test_execute_batch_failure(self):
        """배치 쿼리 실패"""
        env_vars = {
            "CLOUDFLARE_ACCOUNT_ID": "acc",
            "D1_DATABASE_ID": "db",
            "CLOUDFLARE_API_TOKEN": "token",
        }
        with patch.dict("os.environ", env_vars, clear=True):
            client = D1Client()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "success": False,
                "errors": [{"message": "Batch error"}],
            }
            mock_response.raise_for_status = MagicMock()

            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

                with pytest.raises(RuntimeError, match="D1 batch query failed"):
                    await client.execute_batch([{"sql": "INVALID"}])

    @pytest.mark.asyncio
    async def test_health_check_not_configured(self):
        """미설정 상태에서 헬스체크"""
        with patch.dict("os.environ", {}, clear=True):
            client = D1Client()

            result = await client.health_check()

            assert result is False

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """헬스체크 성공"""
        env_vars = {
            "CLOUDFLARE_ACCOUNT_ID": "acc",
            "D1_DATABASE_ID": "db",
            "CLOUDFLARE_API_TOKEN": "token",
        }
        with patch.dict("os.environ", env_vars, clear=True):
            client = D1Client()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "success": True,
                "result": [{"results": [{"health": 1}], "meta": {}}],
            }

            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

                result = await client.health_check()

                assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """헬스체크 실패"""
        env_vars = {
            "CLOUDFLARE_ACCOUNT_ID": "acc",
            "D1_DATABASE_ID": "db",
            "CLOUDFLARE_API_TOKEN": "token",
        }
        with patch.dict("os.environ", env_vars, clear=True):
            client = D1Client()

            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(side_effect=Exception("Connection error"))
                mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

                result = await client.health_check()

                assert result is False

"""
Confluence MCP Server 단위 테스트

ConfluenceMCP 클래스의 각 메서드를 테스트합니다.
"""

from unittest.mock import MagicMock, patch

import pytest

from backend.integrations.mcp_confluence.server import MCP_TOOLS, ConfluenceMCP

# ========== Fixtures ==========


@pytest.fixture
def mock_confluence_env(monkeypatch):
    """Confluence 환경변수 Mock"""
    monkeypatch.setenv("CONFLUENCE_BASE_URL", "https://test.atlassian.net")
    monkeypatch.setenv("CONFLUENCE_API_TOKEN", "test-token")
    monkeypatch.setenv("CONFLUENCE_USER_EMAIL", "test@example.com")
    monkeypatch.setenv("CONFLUENCE_SPACE_KEY", "TEST")
    return monkeypatch


@pytest.fixture
def confluence_mcp(mock_confluence_env):
    """ConfluenceMCP 인스턴스"""
    return ConfluenceMCP()


@pytest.fixture
def confluence_mcp_no_creds():
    """인증 정보 미설정 ConfluenceMCP 인스턴스"""
    with patch.dict(
        "os.environ",
        {
            "CONFLUENCE_BASE_URL": "",
            "CONFLUENCE_API_TOKEN": "",
            "CONFLUENCE_USER_EMAIL": "",
        },
        clear=False,
    ):
        return ConfluenceMCP()


@pytest.fixture
def mock_confluence_client():
    """atlassian.Confluence 클라이언트 Mock"""
    mock_client = MagicMock()
    return mock_client


# ========== 초기화 테스트 ==========


class TestConfluenceMCPInit:
    """ConfluenceMCP 초기화 테스트"""

    def test_init_with_env(self, mock_confluence_env):
        """환경변수로 초기화"""
        mcp = ConfluenceMCP()
        assert mcp.base_url == "https://test.atlassian.net"
        assert mcp.api_token == "test-token"
        assert mcp.user_email == "test@example.com"
        assert mcp.space_key == "TEST"

    def test_init_without_env(self, monkeypatch):
        """환경변수 없이 초기화"""
        monkeypatch.setenv("CONFLUENCE_BASE_URL", "")
        monkeypatch.setenv("CONFLUENCE_API_TOKEN", "")
        monkeypatch.setenv("CONFLUENCE_USER_EMAIL", "")
        monkeypatch.delenv("CONFLUENCE_SPACE_KEY", raising=False)

        mcp = ConfluenceMCP()
        assert mcp.base_url == ""
        assert mcp.space_key == "AXBD"  # 기본값

    def test_client_not_configured(self, confluence_mcp_no_creds):
        """인증 정보 미설정 시 클라이언트 접근 실패"""
        with pytest.raises(ValueError, match="Confluence credentials not configured"):
            _ = confluence_mcp_no_creds.client

    def test_client_lazy_init(self, confluence_mcp):
        """클라이언트 지연 초기화"""
        assert confluence_mcp._client is None

        with patch("backend.integrations.mcp_confluence.server.Confluence") as mock_cls:
            mock_cls.return_value = MagicMock()
            client = confluence_mcp.client

            assert client is not None
            mock_cls.assert_called_once_with(
                url="https://test.atlassian.net",
                username="test@example.com",
                password="test-token",
                cloud=True,
            )


# ========== search_pages 테스트 ==========


class TestSearchPages:
    """search_pages 메서드 테스트"""

    @pytest.mark.asyncio
    async def test_search_pages_success(self, confluence_mcp, mock_confluence_client):
        """페이지 검색 성공"""
        mock_confluence_client.cql.return_value = {
            "results": [
                {
                    "content": {
                        "id": "12345",
                        "title": "테스트 페이지",
                        "_links": {"webui": "/spaces/TEST/pages/12345"},
                    }
                },
                {
                    "content": {
                        "id": "67890",
                        "title": "또 다른 페이지",
                        "_links": {"webui": "/spaces/TEST/pages/67890"},
                    }
                },
            ]
        }
        confluence_mcp._client = mock_confluence_client

        result = await confluence_mcp.search_pages(query="테스트", limit=10)

        assert result["total"] == 2
        assert len(result["pages"]) == 2
        assert result["pages"][0]["id"] == "12345"
        assert result["pages"][0]["title"] == "테스트 페이지"
        mock_confluence_client.cql.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_pages_empty_result(self, confluence_mcp, mock_confluence_client):
        """검색 결과 없음"""
        mock_confluence_client.cql.return_value = {"results": []}
        confluence_mcp._client = mock_confluence_client

        result = await confluence_mcp.search_pages(query="존재하지않는쿼리")

        assert result["total"] == 0
        assert result["pages"] == []

    @pytest.mark.asyncio
    async def test_search_pages_error(self, confluence_mcp, mock_confluence_client):
        """검색 오류"""
        mock_confluence_client.cql.side_effect = Exception("API Error")
        confluence_mcp._client = mock_confluence_client

        with pytest.raises(Exception, match="API Error"):
            await confluence_mcp.search_pages(query="테스트")


# ========== get_page 테스트 ==========


class TestGetPage:
    """get_page 메서드 테스트"""

    @pytest.mark.asyncio
    async def test_get_page_success(self, confluence_mcp, mock_confluence_client):
        """페이지 조회 성공"""
        mock_confluence_client.get_page_by_id.return_value = {
            "id": "12345",
            "title": "테스트 페이지",
            "body": {"storage": {"value": "<p>페이지 내용</p>"}},
            "version": {"number": 5},
            "_links": {"webui": "/spaces/TEST/pages/12345"},
        }
        confluence_mcp._client = mock_confluence_client

        result = await confluence_mcp.get_page(page_id="12345")

        assert result["id"] == "12345"
        assert result["title"] == "테스트 페이지"
        assert result["body"] == "<p>페이지 내용</p>"
        assert result["version"] == 5
        mock_confluence_client.get_page_by_id.assert_called_once_with(
            "12345", expand="body.storage,version"
        )

    @pytest.mark.asyncio
    async def test_get_page_not_found(self, confluence_mcp, mock_confluence_client):
        """페이지 없음"""
        mock_confluence_client.get_page_by_id.side_effect = Exception("Page not found")
        confluence_mcp._client = mock_confluence_client

        with pytest.raises(Exception, match="Page not found"):
            await confluence_mcp.get_page(page_id="99999")


# ========== create_page 테스트 ==========


class TestCreatePage:
    """create_page 메서드 테스트"""

    @pytest.mark.asyncio
    async def test_create_page_success(self, confluence_mcp, mock_confluence_client):
        """페이지 생성 성공"""
        mock_confluence_client.create_page.return_value = {"id": "11111"}
        confluence_mcp._client = mock_confluence_client

        result = await confluence_mcp.create_page(
            title="새 페이지",
            body_md="페이지 내용입니다.",
        )

        assert result["page_id"] == "11111"
        assert result["title"] == "새 페이지"
        assert "url" in result
        mock_confluence_client.create_page.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_page_with_parent(self, confluence_mcp, mock_confluence_client):
        """부모 페이지 지정하여 생성"""
        mock_confluence_client.create_page.return_value = {"id": "22222"}
        confluence_mcp._client = mock_confluence_client

        result = await confluence_mcp.create_page(
            title="자식 페이지",
            body_md="내용",
            parent_id="12345",
        )

        assert result["page_id"] == "22222"
        call_kwargs = mock_confluence_client.create_page.call_args.kwargs
        assert call_kwargs["parent_id"] == "12345"

    @pytest.mark.asyncio
    async def test_create_page_with_labels(self, confluence_mcp, mock_confluence_client):
        """라벨 포함 페이지 생성"""
        mock_confluence_client.create_page.return_value = {"id": "33333"}
        confluence_mcp._client = mock_confluence_client

        result = await confluence_mcp.create_page(
            title="라벨 페이지",
            body_md="내용",
            labels=["label1", "label2"],
        )

        assert result["page_id"] == "33333"
        # 라벨 2개가 추가되었는지 확인
        assert mock_confluence_client.set_page_label.call_count == 2

    @pytest.mark.asyncio
    async def test_create_page_error(self, confluence_mcp, mock_confluence_client):
        """페이지 생성 오류"""
        mock_confluence_client.create_page.side_effect = Exception("Permission denied")
        confluence_mcp._client = mock_confluence_client

        with pytest.raises(Exception, match="Permission denied"):
            await confluence_mcp.create_page(title="테스트", body_md="내용")


# ========== update_page 테스트 ==========


class TestUpdatePage:
    """update_page 메서드 테스트"""

    @pytest.mark.asyncio
    async def test_update_page_success(self, confluence_mcp, mock_confluence_client):
        """페이지 수정 성공"""
        mock_confluence_client.get_page_by_id.return_value = {
            "id": "12345",
            "title": "기존 페이지",
            "body": {"storage": {"value": "<p>기존 내용</p>"}},
            "version": {"number": 3},
            "_links": {"webui": "/spaces/TEST/pages/12345"},
        }
        mock_confluence_client.update_page.return_value = {
            "version": {"number": 4},
        }
        confluence_mcp._client = mock_confluence_client

        result = await confluence_mcp.update_page(
            page_id="12345",
            body_md="새 내용입니다.",
        )

        assert result["page_id"] == "12345"
        assert result["version"] == 4
        mock_confluence_client.update_page.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_page_with_version(self, confluence_mcp, mock_confluence_client):
        """버전 지정하여 수정"""
        mock_confluence_client.get_page_by_id.return_value = {
            "id": "12345",
            "title": "페이지",
            "body": {"storage": {"value": ""}},
            "version": {"number": 5},
            "_links": {"webui": "/test"},
        }
        mock_confluence_client.update_page.return_value = {"version": {"number": 6}}
        confluence_mcp._client = mock_confluence_client

        result = await confluence_mcp.update_page(
            page_id="12345",
            body_md="내용",
            version=5,
        )

        assert result["version"] == 6


# ========== append_to_page 테스트 ==========


class TestAppendToPage:
    """append_to_page 메서드 테스트"""

    @pytest.mark.asyncio
    async def test_append_to_page_success(self, confluence_mcp, mock_confluence_client):
        """페이지에 내용 추가 성공"""
        mock_confluence_client.get_page_by_id.return_value = {
            "id": "12345",
            "title": "페이지",
            "body": {"storage": {"value": "<p>기존 내용</p>"}},
            "version": {"number": 1},
            "_links": {"webui": "/test"},
        }
        mock_confluence_client.update_page.return_value = {"version": {"number": 2}}
        confluence_mcp._client = mock_confluence_client

        result = await confluence_mcp.append_to_page(
            page_id="12345",
            append_md="추가 내용",
        )

        assert result["page_id"] == "12345"
        assert result["version"] == 2


# ========== add_labels 테스트 ==========


class TestAddLabels:
    """add_labels 메서드 테스트"""

    @pytest.mark.asyncio
    async def test_add_labels_success(self, confluence_mcp, mock_confluence_client):
        """라벨 추가 성공"""
        confluence_mcp._client = mock_confluence_client

        result = await confluence_mcp.add_labels(
            page_id="12345",
            labels=["signal", "brief", "2026"],
        )

        assert result["page_id"] == "12345"
        assert result["labels"] == ["signal", "brief", "2026"]
        assert mock_confluence_client.set_page_label.call_count == 3

    @pytest.mark.asyncio
    async def test_add_labels_empty(self, confluence_mcp, mock_confluence_client):
        """빈 라벨 리스트"""
        confluence_mcp._client = mock_confluence_client

        result = await confluence_mcp.add_labels(page_id="12345", labels=[])

        assert result["labels"] == []
        mock_confluence_client.set_page_label.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_labels_error(self, confluence_mcp, mock_confluence_client):
        """라벨 추가 오류"""
        mock_confluence_client.set_page_label.side_effect = Exception("Invalid label")
        confluence_mcp._client = mock_confluence_client

        with pytest.raises(Exception, match="Invalid label"):
            await confluence_mcp.add_labels(page_id="12345", labels=["invalid@label"])


# ========== DB Tools 테스트 (PostgreSQL 위임, Deprecated) ==========


class TestDBTools:
    """DB Tools 테스트 - PostgreSQL 위임 및 Deprecated 안내"""

    @pytest.mark.asyncio
    async def test_db_query_deprecated(self, confluence_mcp):
        """DB 조회 - Deprecated 응답 확인"""
        result = await confluence_mcp.db_query(database_id="db-001")

        assert result["rows"] == []
        assert result["total"] == 0
        assert result["deprecated"] is True
        assert "PostgreSQL" in result["message"]
        assert "play_record_repo" in result["alternative"]

    @pytest.mark.asyncio
    async def test_db_query_with_filters(self, confluence_mcp):
        """필터 포함 DB 조회 - Deprecated 응답"""
        result = await confluence_mcp.db_query(
            database_id="db-001",
            filters={"status": "active"},
        )

        assert result["rows"] == []
        assert result["deprecated"] is True

    @pytest.mark.asyncio
    async def test_db_upsert_row_deprecated(self, confluence_mcp):
        """DB 행 업데이트/삽입 - Deprecated 응답 확인"""
        result = await confluence_mcp.db_upsert_row(
            database_id="db-001",
            row_id="row-123",
            data={"name": "테스트", "value": 100},
        )

        assert result["row_id"] == "row-123"
        assert result["status"] == "deprecated"
        assert result["deprecated"] is True
        assert "play_sync_service" in result["alternative"]

    @pytest.mark.asyncio
    async def test_db_insert_row_deprecated(self, confluence_mcp):
        """DB 행 삽입 - Deprecated 응답 확인"""
        result = await confluence_mcp.db_insert_row(
            database_id="db-001",
            data={"name": "새 행"},
        )

        assert result["status"] == "deprecated"
        assert result["deprecated"] is True
        assert "play_record_repo" in result["alternative"]


# ========== increment_play_activity_count 테스트 ==========


class TestIncrementPlayActivityCount:
    """increment_play_activity_count 메서드 테스트"""

    @pytest.mark.asyncio
    async def test_increment_success(self, confluence_mcp, mock_confluence_client):
        """Play activity count 증가 성공"""
        # 테이블이 포함된 페이지 내용
        table_body = """
        | Play ID | Name | Owner | Activity Count |
        | PLAY-001 | AI Platform | Kim | 5 |
        | PLAY-002 | Cloud Service | Lee | 10 |
        """
        mock_confluence_client.get_page_by_id.return_value = {
            "id": "12345",
            "title": "Play DB",
            "body": {"storage": {"value": table_body}},
            "version": {"number": 1},
            "_links": {"webui": "/test"},
        }
        mock_confluence_client.update_page.return_value = {"version": {"number": 2}}
        confluence_mcp._client = mock_confluence_client

        result = await confluence_mcp.increment_play_activity_count(
            page_id="12345",
            play_id="PLAY-001",
        )

        assert result["status"] == "updated"
        assert result["play_id"] == "PLAY-001"

    @pytest.mark.asyncio
    async def test_increment_not_found(self, confluence_mcp, mock_confluence_client):
        """Play ID 찾을 수 없음"""
        mock_confluence_client.get_page_by_id.return_value = {
            "id": "12345",
            "title": "Play DB",
            "body": {"storage": {"value": "| PLAY-999 | Test | Owner | 1 |"}},
            "version": {"number": 1},
            "_links": {"webui": "/test"},
        }
        confluence_mcp._client = mock_confluence_client

        result = await confluence_mcp.increment_play_activity_count(
            page_id="12345",
            play_id="PLAY-NOT-EXIST",
        )

        assert result["status"] == "not_found"


# ========== 유틸리티 테스트 (Markdown 변환) ==========


class TestMarkdownToConfluence:
    """Markdown to Confluence 변환 테스트"""

    def test_simple_text(self, confluence_mcp):
        """간단한 텍스트 변환"""
        result = confluence_mcp._markdown_to_confluence("Hello World")
        assert "<p>Hello World</p>" in result

    def test_headers(self, confluence_mcp):
        """헤더 변환 (h1~h6)"""
        md = "# 제목 1\n## 제목 2\n### 제목 3"
        result = confluence_mcp._markdown_to_confluence(md)
        assert "<h1" in result
        assert "<h2" in result
        assert "<h3" in result
        assert "제목 1" in result
        assert "제목 2" in result
        assert "제목 3" in result

    def test_bold_and_italic(self, confluence_mcp):
        """강조 (bold, italic) 변환"""
        md = "이것은 **굵은 글씨**와 *기울인 글씨*입니다."
        result = confluence_mcp._markdown_to_confluence(md)
        assert "<strong>굵은 글씨</strong>" in result
        assert "<em>기울인 글씨</em>" in result

    def test_links(self, confluence_mcp):
        """링크 변환"""
        md = "[구글](https://google.com)로 이동"
        result = confluence_mcp._markdown_to_confluence(md)
        assert '<a href="https://google.com">구글</a>' in result

    def test_unordered_list(self, confluence_mcp):
        """비순서 목록 변환"""
        md = "- 항목 1\n- 항목 2\n- 항목 3"
        result = confluence_mcp._markdown_to_confluence(md)
        assert "<ul>" in result
        assert "<li>" in result
        assert "항목 1" in result
        assert "항목 3" in result

    def test_ordered_list(self, confluence_mcp):
        """순서 목록 변환"""
        md = "1. 첫 번째\n2. 두 번째\n3. 세 번째"
        result = confluence_mcp._markdown_to_confluence(md)
        assert "<ol>" in result
        assert "<li>" in result
        assert "첫 번째" in result

    def test_table(self, confluence_mcp):
        """테이블 변환"""
        md = """| 이름 | 나이 |
| --- | --- |
| 홍길동 | 30 |
| 김철수 | 25 |"""
        result = confluence_mcp._markdown_to_confluence(md)
        assert '<table class="wrapped">' in result
        assert '<th class="confluenceTh">' in result
        assert '<td class="confluenceTd">' in result
        assert "홍길동" in result
        assert "30" in result

    def test_code_block_with_language(self, confluence_mcp):
        """언어 지정 코드 블록 변환"""
        md = """```python
def hello():
    print("Hello")
```"""
        result = confluence_mcp._markdown_to_confluence(md)
        assert "ac:structured-macro" in result
        assert 'ac:name="code"' in result
        assert "def hello():" in result
        assert 'print("Hello")' in result

    def test_code_block_without_language(self, confluence_mcp):
        """언어 미지정 코드 블록 변환"""
        md = """```
plain code
```"""
        result = confluence_mcp._markdown_to_confluence(md)
        # markdown2는 언어 없는 코드 블록도 처리함
        assert "plain code" in result

    def test_inline_code(self, confluence_mcp):
        """인라인 코드 변환"""
        md = "변수 `foo`를 사용합니다."
        result = confluence_mcp._markdown_to_confluence(md)
        assert "<code>foo</code>" in result

    def test_strikethrough(self, confluence_mcp):
        """취소선 변환"""
        md = "~~삭제된 텍스트~~"
        result = confluence_mcp._markdown_to_confluence(md)
        # markdown2는 ~~text~~를 <s>text</s>로 변환, 이후 <span style>로 변환됨
        assert "line-through" in result
        assert "삭제된 텍스트" in result

    def test_empty_string(self, confluence_mcp):
        """빈 문자열 변환"""
        result = confluence_mcp._markdown_to_confluence("")
        assert result == ""

    def test_whitespace_only(self, confluence_mcp):
        """공백만 있는 문자열 변환"""
        result = confluence_mcp._markdown_to_confluence("   \n\t  ")
        assert result == ""

    def test_complex_document(self, confluence_mcp):
        """복합 문서 변환 (라운드트립 테스트)"""
        md = """# Signal 요약

## 기본 정보

| 항목 | 값 |
| --- | --- |
| Signal ID | SIG-001 |
| Play ID | PLAY-001 |

## Pain Point

고객사가 **레거시 시스템**을 클라우드로 이전하고 싶어합니다.

### 근거

1. 운영 비용 절감
2. 확장성 확보
3. 보안 강화

자세한 내용은 [여기](https://example.com)를 참조하세요.

```python
# 예시 코드
print("Hello, World!")
```
"""
        result = confluence_mcp._markdown_to_confluence(md)

        # 헤더 확인
        assert "<h1" in result
        assert "<h2" in result
        assert "<h3" in result

        # 테이블 확인
        assert '<table class="wrapped">' in result
        assert "SIG-001" in result

        # 강조 확인
        assert "<strong>레거시 시스템</strong>" in result

        # 목록 확인
        assert "<ol>" in result
        assert "운영 비용 절감" in result

        # 링크 확인
        assert '<a href="https://example.com">' in result

        # 코드 블록 확인 - Confluence 매크로로 변환됨
        assert "ac:structured-macro" in result
        assert 'print("Hello, World!")' in result


# ========== MCP_TOOLS 스키마 테스트 ==========


class TestMCPTools:
    """MCP_TOOLS 스키마 테스트"""

    def test_tools_count(self):
        """도구 개수 확인"""
        assert len(MCP_TOOLS) == 6

    def test_tools_names(self):
        """도구 이름 확인"""
        expected_names = [
            "confluence.search_pages",
            "confluence.get_page",
            "confluence.create_page",
            "confluence.update_page",
            "confluence.append_to_page",
            "confluence.db_upsert_row",
        ]
        actual_names = [tool["name"] for tool in MCP_TOOLS]
        assert actual_names == expected_names

    def test_tools_have_required_fields(self):
        """도구 필수 필드 확인"""
        for tool in MCP_TOOLS:
            assert "name" in tool
            assert "description" in tool
            assert "parameters" in tool
            assert "type" in tool["parameters"]
            assert "properties" in tool["parameters"]

    def test_search_pages_schema(self):
        """search_pages 스키마 확인"""
        tool = next(t for t in MCP_TOOLS if t["name"] == "confluence.search_pages")
        props = tool["parameters"]["properties"]
        assert "query" in props
        assert "limit" in props
        assert tool["parameters"]["required"] == ["query"]

    def test_create_page_schema(self):
        """create_page 스키마 확인"""
        tool = next(t for t in MCP_TOOLS if t["name"] == "confluence.create_page")
        props = tool["parameters"]["properties"]
        assert "title" in props
        assert "body_md" in props
        assert "parent_id" in props
        assert "labels" in props
        assert set(tool["parameters"]["required"]) == {"title", "body_md"}

    def test_update_page_schema(self):
        """update_page 스키마 확인"""
        tool = next(t for t in MCP_TOOLS if t["name"] == "confluence.update_page")
        props = tool["parameters"]["properties"]
        assert "page_id" in props
        assert "body_md" in props
        assert "version" in props

    def test_db_upsert_row_schema(self):
        """db_upsert_row 스키마 확인"""
        tool = next(t for t in MCP_TOOLS if t["name"] == "confluence.db_upsert_row")
        props = tool["parameters"]["properties"]
        assert "database_id" in props
        assert "row_id" in props
        assert "data" in props

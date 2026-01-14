"""
Workflow 단위 테스트

backend/agent_runtime/workflows/wf_seminar_pipeline.py 테스트
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from backend.agent_runtime.workflows.wf_seminar_pipeline import (
    SeminarPipeline,
    SeminarInput,
    ActivityOutput,
    AARTemplate,
)


class TestMetadataExtraction:
    """메타데이터 추출 테스트"""

    @pytest.mark.asyncio
    async def test_extract_metadata_success(self, mock_httpx_response):
        """HTML 파싱 성공 테스트 (httpx Mock)"""
        pipeline = SeminarPipeline()

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_httpx_response
            MockClient.return_value.__aenter__.return_value = mock_client

            # 메타데이터 추출
            metadata = await pipeline._extract_metadata("https://example.com/seminar")

            # 검증
            assert metadata["url"] == "https://example.com/seminar"
            assert metadata["title"] == "Test Seminar Title"
            assert "fetched_at" in metadata
            mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_metadata_network_error(self):
        """네트워크 오류 fallback 테스트"""
        pipeline = SeminarPipeline()

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("Network error")
            MockClient.return_value.__aenter__.return_value = mock_client

            # 메타데이터 추출 (fallback)
            metadata = await pipeline._extract_metadata("https://example.com/seminar")

            # 검증: fallback 값 반환
            assert metadata["title"] == "세미나"
            assert metadata["description"] == ""
            assert metadata["date"] is None

    def test_extract_title_from_og_tag(self):
        """Open Graph 태그 추출 테스트"""
        pipeline = SeminarPipeline()

        html = """
        <html>
        <head>
            <meta property="og:title" content="AI Summit 2026">
        </head>
        </html>
        """

        title = pipeline._extract_title(html)
        assert title == "AI Summit 2026"

    def test_extract_date_korean_format(self):
        """한글 날짜 추출 테스트"""
        pipeline = SeminarPipeline()

        html = """
        <div class="date">2026년 3월 15일</div>
        """

        date = pipeline._extract_date(html)
        assert date == "2026년 3월 15일"

    def test_extract_date_iso_format(self):
        """ISO 날짜 형식 추출 테스트"""
        pipeline = SeminarPipeline()

        html = """
        <div class="date">2026-03-15</div>
        """

        date = pipeline._extract_date(html)
        assert date == "2026-03-15"

    def test_extract_organizer(self):
        """주최자 추출 테스트"""
        pipeline = SeminarPipeline()

        html = """
        <div>주최: KT Corporation</div>
        """

        organizer = pipeline._extract_organizer(html)
        assert "KT Corporation" in organizer


class TestActivityCreation:
    """Activity 생성 테스트"""

    @pytest.mark.asyncio
    async def test_create_activity(self):
        """Activity 객체 생성 및 ID 형식 확인"""
        pipeline = SeminarPipeline()

        input_data = SeminarInput(
            url="https://example.com/seminar",
            themes=["AI", "Cloud"],
            play_id="EXT_Desk_D01_Seminar"
        )

        metadata = {
            "title": "Test Seminar",
            "description": "Test description",
            "date": "2026-03-15",
            "organizer": "Test Org"
        }

        # Activity 생성
        activity = await pipeline._create_activity(input_data, metadata)

        # 검증
        assert activity.activity_id.startswith("ACT-")
        assert activity.title == "Test Seminar"
        assert activity.source == "대외"
        assert activity.channel == "데스크리서치"
        assert activity.play_id == "EXT_Desk_D01_Seminar"
        assert activity.url == "https://example.com/seminar"
        assert activity.status == "REGISTERED"
        assert activity.metadata["themes"] == ["AI", "Cloud"]
        assert activity.metadata["organizer"] == "Test Org"

    @pytest.mark.asyncio
    async def test_create_activity_with_defaults(self):
        """기본값으로 Activity 생성 테스트"""
        pipeline = SeminarPipeline()

        input_data = SeminarInput(url="https://example.com/seminar")
        metadata = {"title": "Seminar"}

        activity = await pipeline._create_activity(input_data, metadata)

        # 기본값 검증
        assert activity.metadata["themes"] == []
        assert activity.date is None


class TestAARTemplateGeneration:
    """AAR 템플릿 생성 테스트"""

    @pytest.mark.asyncio
    async def test_generate_aar_template(self):
        """AAR 템플릿 내용 확인"""
        pipeline = SeminarPipeline()

        activity = ActivityOutput(
            activity_id="ACT-2026-001",
            title="Test Seminar",
            source="대외",
            channel="데스크리서치",
            play_id="EXT_Desk_D01_Seminar",
            url="https://example.com",
            date="2026-03-15",
            status="REGISTERED",
            metadata={}
        )

        metadata = {
            "organizer": "Test Org",
            "description": "Test description"
        }

        # AAR 템플릿 생성
        aar = await pipeline._generate_aar_template(activity, metadata)

        # 검증
        assert aar.activity_id == "ACT-2026-001"
        assert "After Action Review: Test Seminar" in aar.content
        assert "2026-03-15" in aar.content
        assert "Test Org" in aar.content
        assert "핵심 인사이트" in aar.content
        assert "Follow-up Actions" in aar.content
        assert "Signal 후보" in aar.content

    @pytest.mark.asyncio
    async def test_aar_template_with_missing_date(self):
        """날짜 없을 때 AAR 템플릿 생성"""
        pipeline = SeminarPipeline()

        activity = ActivityOutput(
            activity_id="ACT-2026-002",
            title="Test",
            source="대외",
            channel="데스크리서치",
            play_id="TEST",
            url="https://example.com",
            date=None,  # 날짜 없음
            status="REGISTERED",
            metadata={}
        )

        aar = await pipeline._generate_aar_template(activity, {})

        # TBD 확인
        assert "TBD" in aar.content


class TestConfluenceUpdate:
    """Confluence 업데이트 테스트"""

    @pytest.mark.asyncio
    async def test_update_confluence_success(self, mock_confluence_mcp):
        """업데이트 성공 테스트 (Mock)"""
        pipeline = SeminarPipeline()

        # ConfluenceMCP Mock 주입
        with patch("backend.agent_runtime.workflows.wf_seminar_pipeline.ConfluenceMCP") as MockMCP:
            MockMCP.return_value = mock_confluence_mcp

            activity = ActivityOutput(
                activity_id="ACT-2026-001",
                title="Test",
                source="대외",
                channel="데스크리서치",
                play_id="EXT_Desk_D01_Seminar",
                url="https://example.com",
                date=None,
                status="REGISTERED",
                metadata={}
            )

            # Confluence 업데이트
            result = await pipeline._update_confluence(activity)

            # 검증
            assert result is True

    @pytest.mark.asyncio
    async def test_update_confluence_error(self):
        """업데이트 실패 시 False 반환 테스트"""
        pipeline = SeminarPipeline()

        with patch("backend.agent_runtime.workflows.wf_seminar_pipeline.ConfluenceMCP") as MockMCP:
            mock_mcp = AsyncMock()
            mock_mcp.append_to_page.side_effect = Exception("Confluence error")
            MockMCP.return_value = mock_mcp

            activity = ActivityOutput(
                activity_id="ACT-2026-001",
                title="Test",
                source="대외",
                channel="데스크리서치",
                play_id="EXT_Desk_D01_Seminar",
                url="https://example.com",
                date=None,
                status="REGISTERED",
                metadata={}
            )

            # Confluence 업데이트 (실패)
            result = await pipeline._update_confluence(activity)

            # 검증: False 반환
            assert result is False


class TestSeminarPipelineIntegration:
    """전체 워크플로 통합 테스트"""

    @pytest.mark.asyncio
    async def test_run_pipeline_end_to_end(self, mock_httpx_response, mock_confluence_mcp):
        """WF-01 전체 실행 테스트"""
        pipeline = SeminarPipeline()

        input_data = SeminarInput(
            url="https://example.com/seminar",
            themes=["AI"],
            play_id="EXT_Desk_D01_Seminar"
        )

        with patch("httpx.AsyncClient") as MockClient, \
             patch("backend.agent_runtime.workflows.wf_seminar_pipeline.ConfluenceMCP") as MockMCP:

            # httpx Mock
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_httpx_response
            MockClient.return_value.__aenter__.return_value = mock_client

            # Confluence Mock
            MockMCP.return_value = mock_confluence_mcp

            # 파이프라인 실행
            result = await pipeline.run(input_data)

            # 검증
            assert result.activity is not None
            assert result.activity.activity_id.startswith("ACT-")
            assert result.activity.title == "Test Seminar Title"

            assert result.aar_template is not None
            assert "After Action Review" in result.aar_template.content

            assert result.signals == []  # 초기에는 빈 목록
            assert result.confluence_live_doc_updated is True

    @pytest.mark.asyncio
    async def test_run_with_network_failure(self):
        """네트워크 실패 시에도 파이프라인 완료 테스트"""
        pipeline = SeminarPipeline()

        input_data = SeminarInput(url="https://example.com/seminar")

        with patch("httpx.AsyncClient") as MockClient, \
             patch("backend.agent_runtime.workflows.wf_seminar_pipeline.ConfluenceMCP") as MockMCP:

            # 네트워크 오류 시뮬레이션
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("Network error")
            MockClient.return_value.__aenter__.return_value = mock_client

            # Confluence Mock
            mock_mcp = AsyncMock()
            mock_mcp.append_to_page.return_value = {"success": True}
            MockMCP.return_value = mock_mcp

            # 파이프라인 실행 (fallback으로 완료)
            result = await pipeline.run(input_data)

            # 검증: fallback 값으로 완료
            assert result.activity.title == "세미나"
            assert result.aar_template is not None


class TestHelperMethods:
    """헬퍼 메서드 테스트"""

    def test_extract_meta_with_name_attribute(self):
        """meta 태그 name 속성 추출 테스트"""
        pipeline = SeminarPipeline()

        html = """
        <meta name="description" content="Test description">
        """

        description = pipeline._extract_meta(html, "description")
        assert description == "Test description"

    def test_extract_meta_with_property_attribute(self):
        """meta 태그 property 속성 추출 테스트"""
        pipeline = SeminarPipeline()

        html = """
        <meta property="og:description" content="OG description">
        """

        description = pipeline._extract_meta(html, "description")
        assert description == "OG description"

    def test_extract_meta_not_found(self):
        """meta 태그 없을 때 빈 문자열 반환 테스트"""
        pipeline = SeminarPipeline()

        html = "<html><head></head></html>"

        description = pipeline._extract_meta(html, "description")
        assert description == ""

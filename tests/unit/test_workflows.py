"""
Workflow 단위 테스트

backend/agent_runtime/workflows/wf_seminar_pipeline.py 테스트
backend/agent_runtime/workflows/wf_inbound_triage.py 테스트
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from backend.agent_runtime.workflows.wf_seminar_pipeline import (
    SeminarPipeline,
    SeminarInput,
    ActivityOutput,
    AARTemplate,
)
from backend.agent_runtime.workflows.wf_inbound_triage import (
    InboundTriagePipeline,
    InboundInput,
    InboundOutput,
    Urgency,
    SLA_HOURS,
    calculate_text_similarity,
    route_to_play,
    calculate_sla_deadline,
    create_scorecard_draft_from_signal,
    determine_next_action,
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


# ============================================================
# WF-04: Inbound Triage 테스트
# ============================================================

class TestTextSimilarity:
    """텍스트 유사도 계산 테스트"""

    def test_identical_texts(self):
        """동일 텍스트는 1.0 반환"""
        text1 = "AI 기반 콜센터 자동화 솔루션"
        text2 = "AI 기반 콜센터 자동화 솔루션"

        similarity = calculate_text_similarity(text1, text2)
        assert similarity == 1.0

    def test_similar_texts(self):
        """유사 텍스트는 높은 점수"""
        text1 = "AI 기반 콜센터 자동화 솔루션"
        text2 = "AI 콜센터 자동화 서비스"

        similarity = calculate_text_similarity(text1, text2)
        assert 0.4 <= similarity < 1.0  # Jaccard 유사도는 단어 기반이므로 0.5 포함

    def test_different_texts(self):
        """다른 텍스트는 낮은 점수"""
        text1 = "AI 기반 콜센터"
        text2 = "금융 데이터 분석"

        similarity = calculate_text_similarity(text1, text2)
        assert similarity < 0.3

    def test_empty_text(self):
        """빈 텍스트는 0.0 반환"""
        assert calculate_text_similarity("", "test") == 0.0
        assert calculate_text_similarity("test", "") == 0.0
        assert calculate_text_similarity("", "") == 0.0


class TestPlayRouting:
    """Play 라우팅 테스트"""

    def test_route_to_kt_play(self):
        """KT 키워드 → KT_Sales_S01"""
        play_id = route_to_play(
            "KT 콜센터 AI 적용",
            "고객 상담 자동화 필요",
            "KT",
        )
        assert play_id == "KT_Sales_S01"

    def test_route_to_ai_play(self):
        """AI/데이터 키워드 → KT_Desk_D01_AI"""
        play_id = route_to_play(
            "데이터 분석 플랫폼",
            "머신러닝 기반 예측 시스템",
            "금융",
        )
        assert play_id == "KT_Desk_D01_AI"

    def test_route_to_finance_play(self):
        """금융 키워드 → GRP_Sales_S01_Finance"""
        play_id = route_to_play(
            "은행 업무 자동화",
            "금융 서비스 개선",
            "신한은행",
        )
        assert play_id == "GRP_Sales_S01_Finance"

    def test_route_to_default_play(self):
        """매칭 키워드 없으면 기본 Play"""
        play_id = route_to_play(
            "일반 문의",
            "특별한 내용 없음",
            None,
        )
        assert play_id == "KT_Inbound_I01"


class TestSLACalculation:
    """SLA 계산 테스트"""

    def test_urgent_sla(self):
        """URGENT = 24시간"""
        deadline = calculate_sla_deadline("URGENT")
        expected = datetime.utcnow() + timedelta(hours=24)

        # 1분 이내 차이
        assert abs((deadline - expected).total_seconds()) < 60

    def test_normal_sla(self):
        """NORMAL = 48시간"""
        deadline = calculate_sla_deadline("NORMAL")
        expected = datetime.utcnow() + timedelta(hours=48)

        assert abs((deadline - expected).total_seconds()) < 60

    def test_low_sla(self):
        """LOW = 72시간"""
        deadline = calculate_sla_deadline("LOW")
        expected = datetime.utcnow() + timedelta(hours=72)

        assert abs((deadline - expected).total_seconds()) < 60

    def test_invalid_urgency_defaults_to_normal(self):
        """유효하지 않은 긴급도 → NORMAL"""
        deadline = calculate_sla_deadline("INVALID")
        expected = datetime.utcnow() + timedelta(hours=48)

        assert abs((deadline - expected).total_seconds()) < 60


class TestScorecardDraftCreation:
    """Scorecard 초안 생성 테스트"""

    def test_create_scorecard_draft(self):
        """Scorecard 초안 생성 확인"""
        signal = {
            "signal_id": "SIG-2026-TEST001",
            "title": "AI 콜센터 자동화",
            "pain": "고객 상담 대기 시간이 너무 길다",
            "customer_segment": "KT",
        }

        draft = create_scorecard_draft_from_signal(signal)

        assert draft.scorecard_id.startswith("SCR-")
        assert draft.signal_id == "SIG-2026-TEST001"
        assert draft.is_draft is True
        assert 0 <= draft.total_score <= 100
        assert draft.decision in ["GO", "PIVOT", "HOLD", "NO_GO"]

    def test_dimension_scores_exist(self):
        """5개 차원 점수 존재 확인"""
        signal = {
            "signal_id": "SIG-2026-TEST002",
            "title": "테스트",
            "pain": "테스트 Pain Point",
        }

        draft = create_scorecard_draft_from_signal(signal)

        assert "problem_severity" in draft.dimension_scores
        assert "willingness_to_pay" in draft.dimension_scores
        assert "data_availability" in draft.dimension_scores
        assert "feasibility" in draft.dimension_scores
        assert "strategic_fit" in draft.dimension_scores

        # 각 차원 0-20점
        for dim, score in draft.dimension_scores.items():
            assert 0 <= score <= 20


class TestNextActionDetermination:
    """다음 액션 결정 테스트"""

    def test_duplicate_action(self):
        """중복이면 MERGE_OR_CLOSE"""
        action = determine_next_action("GO", is_duplicate=True)
        assert action == "MERGE_OR_CLOSE"

    def test_go_action(self):
        """GO → CREATE_BRIEF"""
        action = determine_next_action("GO", is_duplicate=False)
        assert action == "CREATE_BRIEF"

    def test_pivot_action(self):
        """PIVOT → REVIEW_AND_ENHANCE"""
        action = determine_next_action("PIVOT", is_duplicate=False)
        assert action == "REVIEW_AND_ENHANCE"

    def test_hold_action(self):
        """HOLD → SCHEDULE_FOLLOW_UP"""
        action = determine_next_action("HOLD", is_duplicate=False)
        assert action == "SCHEDULE_FOLLOW_UP"

    def test_nogo_action(self):
        """NO_GO → ARCHIVE"""
        action = determine_next_action("NO_GO", is_duplicate=False)
        assert action == "ARCHIVE"


class TestInboundTriagePipeline:
    """InboundTriagePipeline 테스트"""

    @pytest.mark.asyncio
    async def test_pipeline_run_success(self):
        """파이프라인 성공 실행"""
        pipeline = InboundTriagePipeline()

        input_data = InboundInput(
            title="AI 콜센터 자동화 문의",
            description="고객 상담 대기 시간을 줄이고 싶습니다",
            customer_segment="KT",
            pain="대기 시간이 길어 고객 불만 증가",
            submitter="홍길동",
            urgency="NORMAL",
            source="KT",
        )

        result = await pipeline.run(input_data)

        # 결과 검증
        assert result.signal_id.startswith("SIG-")
        assert result.is_duplicate is False
        assert result.play_id == "KT_Sales_S01"  # KT 키워드 매칭
        assert result.scorecard is not None
        assert result.scorecard["is_draft"] is True
        assert result.next_action in ["CREATE_BRIEF", "REVIEW_AND_ENHANCE", "SCHEDULE_FOLLOW_UP", "ARCHIVE"]
        assert result.sla_deadline is not None

    @pytest.mark.asyncio
    async def test_pipeline_urgent_sla(self):
        """URGENT 긴급도 SLA 확인"""
        pipeline = InboundTriagePipeline()

        input_data = InboundInput(
            title="긴급 요청",
            description="즉시 처리 필요",
            urgency="URGENT",
        )

        result = await pipeline.run(input_data)

        # URGENT는 24시간 SLA
        deadline = datetime.fromisoformat(result.sla_deadline)
        expected_min = datetime.utcnow() + timedelta(hours=23)
        expected_max = datetime.utcnow() + timedelta(hours=25)

        assert expected_min < deadline < expected_max

    @pytest.mark.asyncio
    async def test_pipeline_with_ai_keywords(self):
        """AI 키워드 Play 라우팅 확인"""
        pipeline = InboundTriagePipeline()

        input_data = InboundInput(
            title="머신러닝 모델 개발",
            description="데이터 분석 및 AI 적용 문의",
            source="대외",
        )

        result = await pipeline.run(input_data)

        assert result.play_id == "KT_Desk_D01_AI"

    @pytest.mark.asyncio
    async def test_pipeline_signal_creation(self):
        """Signal 생성 필드 확인"""
        pipeline = InboundTriagePipeline()

        input_data = InboundInput(
            title="테스트 Signal",
            description="테스트 설명",
            customer_segment="테스트 세그먼트",
            pain="테스트 Pain",
            submitter="테스터",
            urgency="LOW",
            source="그룹사",
        )

        # 내부 메서드 직접 테스트
        play_id = route_to_play(
            input_data.title,
            input_data.description,
            input_data.customer_segment,
        )
        signal = await pipeline._create_signal(input_data, play_id)

        assert signal["title"] == "테스트 Signal"
        assert signal["source"] == "그룹사"
        assert signal["channel"] == "인바운드"
        assert signal["pain"] == "테스트 Pain"
        assert signal["owner"] == "테스터"
        assert "inbound" in signal["tags"]
        assert "low" in signal["tags"]


class TestInboundTriagePipelineIntegration:
    """WF-04 통합 테스트"""

    @pytest.mark.asyncio
    async def test_full_pipeline_flow(self):
        """전체 파이프라인 흐름 테스트"""
        pipeline = InboundTriagePipeline()

        input_data = InboundInput(
            title="금융 AI 서비스 문의",
            description="은행 업무 자동화를 위한 AI 솔루션이 필요합니다",
            customer_segment="금융/은행",
            pain="수동 업무로 인한 비효율",
            submitter="김은행",
            urgency="NORMAL",
            source="그룹사",
        )

        result = await pipeline.run(input_data)

        # 전체 흐름 검증
        assert result.signal_id is not None
        assert result.scorecard is not None
        assert result.summary["status"] == "triage_completed"

        # Scorecard 검증
        scorecard = result.scorecard
        assert scorecard["total_score"] >= 0
        assert scorecard["total_score"] <= 100
        assert "recommendation" in scorecard
        assert scorecard["recommendation"]["decision"] in ["GO", "PIVOT", "HOLD", "NO_GO"]

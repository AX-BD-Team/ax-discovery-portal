"""
Workflow 단위 테스트

backend/agent_runtime/workflows/wf_seminar_pipeline.py 테스트
backend/agent_runtime/workflows/wf_inbound_triage.py 테스트
backend/agent_runtime/workflows/wf_kpi_digest.py 테스트
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from backend.agent_runtime.workflows.wf_inbound_triage import (
    InboundInput,
    InboundTriagePipeline,
    calculate_sla_deadline,
    calculate_text_similarity,
    create_scorecard_draft_from_signal,
    determine_next_action,
    route_to_play,
)
from backend.agent_runtime.workflows.wf_seminar_pipeline import (
    ActivityOutput,
    SeminarInput,
    SeminarPipeline,
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

            # 검증 (구현은 <title> 태그 우선, og:title은 fallback)
            assert metadata["url"] == "https://example.com/seminar"
            assert metadata["title"] == "Test Seminar"  # <title> 태그 값
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
            play_id="EXT_Desk_D01_Seminar",
        )

        metadata = {
            "title": "Test Seminar",
            "description": "Test description",
            "date": "2026-03-15",
            "organizer": "Test Org",
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
            metadata={},
        )

        metadata = {"organizer": "Test Org", "description": "Test description"}

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
            metadata={},
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

        # ConfluenceMCP는 메서드 내부에서 import되므로 integrations 경로에서 mock
        with patch("backend.integrations.mcp_confluence.server.ConfluenceMCP") as MockMCP:
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
                metadata={},
            )

            # Confluence 업데이트
            result = await pipeline._update_confluence(activity)

            # 검증
            assert result is True

    @pytest.mark.asyncio
    async def test_update_confluence_error(self, monkeypatch):
        """업데이트 실패 시 False 반환 테스트"""
        # 환경변수 설정 (append_to_page가 호출되도록)
        monkeypatch.setenv("CONFLUENCE_ACTION_LOG_PAGE_ID", "test-page-id")

        pipeline = SeminarPipeline()

        with patch("backend.integrations.mcp_confluence.server.ConfluenceMCP") as MockMCP:
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
                metadata={},
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
            url="https://example.com/seminar", themes=["AI"], play_id="EXT_Desk_D01_Seminar"
        )

        with (
            patch("httpx.AsyncClient") as MockClient,
            patch("backend.integrations.mcp_confluence.server.ConfluenceMCP") as MockMCP,
        ):
            # httpx Mock
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_httpx_response
            MockClient.return_value.__aenter__.return_value = mock_client

            # Confluence Mock
            MockMCP.return_value = mock_confluence_mcp

            # 파이프라인 실행
            result = await pipeline.run(input_data)

            # 검증 (구현은 <title> 태그 우선)
            assert result.activity is not None
            assert result.activity.activity_id.startswith("ACT-")
            assert result.activity.title == "Test Seminar"  # <title> 태그 값

            assert result.aar_template is not None
            assert "After Action Review" in result.aar_template.content

            assert result.signals == []  # 초기에는 빈 목록
            assert result.confluence_live_doc_updated is True

    @pytest.mark.asyncio
    async def test_run_with_network_failure(self):
        """네트워크 실패 시에도 파이프라인 완료 테스트"""
        pipeline = SeminarPipeline()

        input_data = SeminarInput(url="https://example.com/seminar")

        with (
            patch("httpx.AsyncClient") as MockClient,
            patch("backend.integrations.mcp_confluence.server.ConfluenceMCP") as MockMCP,
        ):
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
        expected = datetime.now(UTC) + timedelta(hours=24)

        # 1분 이내 차이
        assert abs((deadline - expected).total_seconds()) < 60

    def test_normal_sla(self):
        """NORMAL = 48시간"""
        deadline = calculate_sla_deadline("NORMAL")
        expected = datetime.now(UTC) + timedelta(hours=48)

        assert abs((deadline - expected).total_seconds()) < 60

    def test_low_sla(self):
        """LOW = 72시간"""
        deadline = calculate_sla_deadline("LOW")
        expected = datetime.now(UTC) + timedelta(hours=72)

        assert abs((deadline - expected).total_seconds()) < 60

    def test_invalid_urgency_defaults_to_normal(self):
        """유효하지 않은 긴급도 → NORMAL"""
        deadline = calculate_sla_deadline("INVALID")
        expected = datetime.now(UTC) + timedelta(hours=48)

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
        for _dim, score in draft.dimension_scores.items():
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
        assert result.next_action in [
            "CREATE_BRIEF",
            "REVIEW_AND_ENHANCE",
            "SCHEDULE_FOLLOW_UP",
            "ARCHIVE",
        ]
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
        expected_min = datetime.now(UTC) + timedelta(hours=23)
        expected_max = datetime.now(UTC) + timedelta(hours=25)

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


# ============================================================
# WF-05: KPI Digest 테스트
# ============================================================

from backend.agent_runtime.workflows.wf_kpi_digest import (
    POC_TARGETS,
    Alert,
    AlertSeverity,
    AlertType,
    KPIDigestOutput,
    KPIDigestPipeline,
    KPIInput,
    KPITarget,
    TopPlay,
    calculate_achievement,
    calculate_period_range,
    determine_severity,
)


class TestPeriodRangeCalculation:
    """기간 범위 계산 테스트"""

    def test_week_period(self):
        """주간 기간 계산"""
        start, end = calculate_period_range("week")

        # 월요일 00:00 시작
        assert start.weekday() == 0
        assert start.hour == 0
        assert start.minute == 0

        # 일요일 23:59 종료
        assert end.weekday() == 6
        assert end.hour == 23
        assert end.minute == 59

        # 7일 차이
        diff = (end - start).days
        assert diff == 6

    def test_month_period(self):
        """월간 기간 계산"""
        start, end = calculate_period_range("month")

        # 1일 시작
        assert start.day == 1
        assert start.hour == 0

        # 말일 종료 (다음 달 1일 -1초)
        next_day = end + timedelta(seconds=1)
        assert next_day.day == 1

    def test_invalid_period_defaults_to_7_days(self):
        """유효하지 않은 기간 → 7일"""
        start, end = calculate_period_range("invalid")

        diff = (end - start).days
        assert diff == 7


class TestAchievementCalculation:
    """달성률 계산 테스트"""

    def test_full_achievement(self):
        """100% 달성"""
        achievement = calculate_achievement(20, 20)
        assert achievement == 100.0

    def test_over_achievement(self):
        """초과 달성"""
        achievement = calculate_achievement(30, 20)
        assert achievement == 150.0

    def test_partial_achievement(self):
        """부분 달성"""
        achievement = calculate_achievement(15, 30)
        assert achievement == 50.0

    def test_zero_target(self):
        """목표 0일 때"""
        # 실적 있으면 100%
        assert calculate_achievement(5, 0) == 100.0
        # 실적 없으면 0%
        assert calculate_achievement(0, 0) == 0.0

    def test_zero_actual(self):
        """실적 0일 때"""
        achievement = calculate_achievement(0, 20)
        assert achievement == 0.0


class TestSeverityDetermination:
    """심각도 결정 테스트"""

    def test_info_severity(self):
        """80% 이상 → INFO"""
        assert determine_severity(100.0) == "INFO"
        assert determine_severity(80.0) == "INFO"
        assert determine_severity(85.5) == "INFO"

    def test_yellow_severity(self):
        """50~79% → YELLOW"""
        assert determine_severity(79.9) == "YELLOW"
        assert determine_severity(50.0) == "YELLOW"
        assert determine_severity(65.0) == "YELLOW"

    def test_red_severity(self):
        """50% 미만 → RED"""
        assert determine_severity(49.9) == "RED"
        assert determine_severity(0.0) == "RED"
        assert determine_severity(30.0) == "RED"


class TestPOCTargets:
    """PoC 목표 상수 테스트"""

    def test_weekly_targets(self):
        """주간 목표 확인"""
        assert POC_TARGETS["activity_weekly"] == 20
        assert POC_TARGETS["signal_weekly"] == 30
        assert POC_TARGETS["brief_weekly"] == 6
        assert POC_TARGETS["s2_weekly_min"] == 2
        assert POC_TARGETS["s2_weekly_max"] == 4

    def test_lead_time_targets(self):
        """리드타임 목표 확인"""
        assert POC_TARGETS["signal_to_brief_days"] == 7
        assert POC_TARGETS["brief_to_s2_days"] == 14


class TestKPITarget:
    """KPITarget 데이터클래스 테스트"""

    def test_default_values(self):
        """기본값 확인"""
        target = KPITarget()

        assert target.activity_weekly == 20
        assert target.signal_weekly == 30
        assert target.brief_weekly == 6
        assert target.s2_weekly_min == 2
        assert target.s2_weekly_max == 4
        assert target.signal_to_brief_days == 7
        assert target.brief_to_s2_days == 14


class TestAlertGeneration:
    """경고 생성 테스트"""

    @pytest.mark.asyncio
    async def test_under_target_alert(self):
        """목표 미달 경고 생성"""
        pipeline = KPIDigestPipeline()

        # 낮은 달성률 메트릭
        metrics = {
            "activity": {"actual": 10, "target": 20, "achievement": 50.0},
            "signal": {"actual": 35, "target": 30, "achievement": 116.7},
            "brief": {"actual": 8, "target": 6, "achievement": 133.3},
            "s2": {"actual": 3, "target_min": 2, "target_max": 4, "achievement": 150.0},
        }

        lead_times = {
            "signal_to_brief": {"avg_days": 5.0, "target_days": 7, "on_target": True},
            "brief_to_s2": {"avg_days": 10.0, "target_days": 14, "on_target": True},
        }

        alerts = await pipeline._generate_alerts(metrics, lead_times)

        # Activity 목표 미달 경고
        under_target_alerts = [a for a in alerts if a.type == AlertType.UNDER_TARGET.value]
        assert len(under_target_alerts) == 1
        assert under_target_alerts[0].metric == "activity"
        assert under_target_alerts[0].severity == AlertSeverity.YELLOW.value

    @pytest.mark.asyncio
    async def test_lead_time_exceeded_alert(self):
        """리드타임 초과 경고 생성"""
        pipeline = KPIDigestPipeline()

        metrics = {
            "activity": {"actual": 25, "target": 20, "achievement": 125.0},
            "signal": {"actual": 35, "target": 30, "achievement": 116.7},
            "brief": {"actual": 8, "target": 6, "achievement": 133.3},
            "s2": {"actual": 3, "target_min": 2, "target_max": 4, "achievement": 150.0},
        }

        lead_times = {
            "signal_to_brief": {"avg_days": 10.0, "target_days": 7, "on_target": False},
            "brief_to_s2": {"avg_days": 18.0, "target_days": 14, "on_target": False},
        }

        alerts = await pipeline._generate_alerts(metrics, lead_times)

        # 리드타임 초과 경고
        lead_time_alerts = [a for a in alerts if a.type == AlertType.LEAD_TIME_EXCEEDED.value]
        assert len(lead_time_alerts) == 2

    @pytest.mark.asyncio
    async def test_s2_under_target_alert(self):
        """S2 목표 미달 경고"""
        pipeline = KPIDigestPipeline()

        metrics = {
            "activity": {"actual": 25, "target": 20, "achievement": 125.0},
            "signal": {"actual": 35, "target": 30, "achievement": 116.7},
            "brief": {"actual": 8, "target": 6, "achievement": 133.3},
            "s2": {"actual": 1, "target_min": 2, "target_max": 4, "achievement": 50.0},
        }

        lead_times = {
            "signal_to_brief": {"avg_days": 5.0, "target_days": 7, "on_target": True},
            "brief_to_s2": {"avg_days": 10.0, "target_days": 14, "on_target": True},
        }

        alerts = await pipeline._generate_alerts(metrics, lead_times)

        # S2 목표 미달 경고
        s2_alerts = [a for a in alerts if a.metric == "s2"]
        assert len(s2_alerts) == 1
        assert s2_alerts[0].severity == AlertSeverity.YELLOW.value


class TestTopPlays:
    """Top Plays 테스트"""

    @pytest.mark.asyncio
    async def test_get_top_plays(self):
        """Top Plays 조회 (Mock 데이터)"""
        pipeline = KPIDigestPipeline()
        start, end = calculate_period_range("week")

        top_plays = await pipeline._get_top_plays(start, end)

        assert len(top_plays) == 3
        assert top_plays[0].rank == 1
        assert top_plays[0].signal_count >= top_plays[1].signal_count

    def test_top_play_to_dict(self):
        """TopPlay → dict 변환"""
        pipeline = KPIDigestPipeline()

        top_play = TopPlay(
            rank=1,
            play_id="TEST_PLAY",
            play_name="테스트 Play",
            signal_count=10,
            brief_count=5,
            s2_count=2,
            owner="테스터",
        )

        result = pipeline._top_play_to_dict(top_play)

        assert result["rank"] == 1
        assert result["play_id"] == "TEST_PLAY"
        assert result["signal_count"] == 10
        assert result["owner"] == "테스터"


class TestRecommendationsGeneration:
    """추천 사항 생성 테스트"""

    def test_activity_recommendation(self):
        """Activity 목표 미달 추천"""
        pipeline = KPIDigestPipeline()

        metrics = {
            "activity": {"achievement": 50.0},
            "signal": {"achievement": 100.0},
            "brief": {"achievement": 100.0},
        }

        alerts = [
            Alert(
                type=AlertType.UNDER_TARGET.value,
                severity=AlertSeverity.YELLOW.value,
                metric="activity",
                message="Activity 목표 대비 50% 달성",
            )
        ]

        recommendations = pipeline._generate_recommendations(metrics, alerts)

        assert any("Activity" in r for r in recommendations)

    def test_signal_recommendation(self):
        """Signal 목표 미달 추천"""
        pipeline = KPIDigestPipeline()

        metrics = {
            "activity": {"achievement": 100.0},
            "signal": {"achievement": 50.0},
            "brief": {"achievement": 100.0},
        }

        alerts = [
            Alert(
                type=AlertType.UNDER_TARGET.value,
                severity=AlertSeverity.YELLOW.value,
                metric="signal",
                message="Signal 목표 대비 50% 달성",
            )
        ]

        recommendations = pipeline._generate_recommendations(metrics, alerts)

        assert any("Signal" in r for r in recommendations)

    def test_lead_time_recommendation(self):
        """리드타임 초과 추천"""
        pipeline = KPIDigestPipeline()

        metrics = {
            "activity": {"achievement": 100.0},
            "signal": {"achievement": 100.0},
            "brief": {"achievement": 100.0},
        }

        alerts = [
            Alert(
                type=AlertType.LEAD_TIME_EXCEEDED.value,
                severity=AlertSeverity.YELLOW.value,
                metric="signal_to_brief",
                message="리드타임 초과",
            )
        ]

        recommendations = pipeline._generate_recommendations(metrics, alerts)

        assert any("리드타임" in r for r in recommendations)

    def test_all_good_recommendation(self):
        """모든 KPI 달성 시 추천"""
        pipeline = KPIDigestPipeline()

        metrics = {
            "activity": {"achievement": 100.0},
            "signal": {"achievement": 100.0},
            "brief": {"achievement": 100.0},
        }

        alerts = []

        recommendations = pipeline._generate_recommendations(metrics, alerts)

        assert any("🎉" in r or "양호" in r for r in recommendations)


class TestKPIDigestPipeline:
    """KPIDigestPipeline 전체 테스트"""

    @pytest.mark.asyncio
    async def test_pipeline_run_week(self):
        """주간 KPI Digest 실행"""
        pipeline = KPIDigestPipeline()

        input_data = KPIInput(
            period="week",
            notify=False,
            include_recommendations=True,
        )

        result = await pipeline.run(input_data)

        assert result.period == "week"
        assert result.period_start is not None
        assert result.period_end is not None
        assert result.metrics is not None
        assert result.lead_times is not None
        assert result.alerts is not None
        assert result.top_plays is not None
        assert result.recommendations is not None
        assert result.status_summary is not None
        assert result.generated_at is not None

    @pytest.mark.asyncio
    async def test_pipeline_run_month(self):
        """월간 KPI Digest 실행"""
        pipeline = KPIDigestPipeline()

        input_data = KPIInput(
            period="month",
            notify=False,
        )

        result = await pipeline.run(input_data)

        assert result.period == "month"

    @pytest.mark.asyncio
    async def test_metrics_structure(self):
        """메트릭 구조 확인"""
        pipeline = KPIDigestPipeline()

        input_data = KPIInput(period="week")
        result = await pipeline.run(input_data)

        # 필수 메트릭 확인
        assert "activity" in result.metrics
        assert "signal" in result.metrics
        assert "brief" in result.metrics
        assert "s2" in result.metrics

        # 메트릭 필드 확인
        for key in ["activity", "signal", "brief"]:
            assert "actual" in result.metrics[key]
            assert "target" in result.metrics[key]
            assert "achievement" in result.metrics[key]

    @pytest.mark.asyncio
    async def test_lead_times_structure(self):
        """리드타임 구조 확인"""
        pipeline = KPIDigestPipeline()

        input_data = KPIInput(period="week")
        result = await pipeline.run(input_data)

        # 필수 리드타임 확인
        assert "signal_to_brief" in result.lead_times
        assert "brief_to_s2" in result.lead_times

        # 리드타임 필드 확인
        for key in ["signal_to_brief", "brief_to_s2"]:
            assert "avg_days" in result.lead_times[key]
            assert "target_days" in result.lead_times[key]
            assert "on_target" in result.lead_times[key]

    @pytest.mark.asyncio
    async def test_status_summary_structure(self):
        """상태 요약 구조 확인"""
        pipeline = KPIDigestPipeline()

        input_data = KPIInput(period="week")
        result = await pipeline.run(input_data)

        # Play 상태 분포 확인
        assert "green" in result.status_summary
        assert "yellow" in result.status_summary
        assert "red" in result.status_summary
        assert "total" in result.status_summary

        # total = green + yellow + red
        total = (
            result.status_summary["green"]
            + result.status_summary["yellow"]
            + result.status_summary["red"]
        )
        assert result.status_summary["total"] == total

    @pytest.mark.asyncio
    async def test_without_recommendations(self):
        """추천 사항 없이 실행"""
        pipeline = KPIDigestPipeline()

        input_data = KPIInput(
            period="week",
            include_recommendations=False,
        )

        result = await pipeline.run(input_data)

        assert result.recommendations == []


class TestKPIDigestPipelineIntegration:
    """WF-05 통합 테스트"""

    @pytest.mark.asyncio
    async def test_full_pipeline_flow(self):
        """전체 파이프라인 흐름 테스트"""
        pipeline = KPIDigestPipeline()

        input_data = KPIInput(
            period="week",
            notify=False,
            include_recommendations=True,
        )

        result = await pipeline.run(input_data)

        # 결과 검증
        assert isinstance(result, KPIDigestOutput)
        assert result.period == "week"

        # 메트릭 달성률 범위 확인
        for key in ["activity", "signal", "brief"]:
            achievement = result.metrics[key]["achievement"]
            assert 0 <= achievement <= 200  # 200%까지 가능

        # 리드타임 범위 확인
        for key in ["signal_to_brief", "brief_to_s2"]:
            avg_days = result.lead_times[key]["avg_days"]
            assert avg_days >= 0

        # 알림이 꺼져있으면 confluence_url은 None
        assert result.confluence_url is None

    @pytest.mark.asyncio
    async def test_alert_to_dict_conversion(self):
        """Alert → dict 변환 확인"""
        pipeline = KPIDigestPipeline()

        alert = Alert(
            type=AlertType.UNDER_TARGET.value,
            severity=AlertSeverity.YELLOW.value,
            metric="activity",
            message="테스트 경고",
            play_id="TEST_PLAY",
            details={"actual": 10, "target": 20},
        )

        result = pipeline._alert_to_dict(alert)

        assert result["type"] == "UNDER_TARGET"
        assert result["severity"] == "YELLOW"
        assert result["metric"] == "activity"
        assert result["message"] == "테스트 경고"
        assert result["play_id"] == "TEST_PLAY"
        assert result["details"]["actual"] == 10

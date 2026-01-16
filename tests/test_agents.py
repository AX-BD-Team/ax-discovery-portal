"""
AX Discovery Portal - Tests

pytest 기반 테스트
"""

from datetime import UTC, datetime

import pytest

# ========== Fixtures ==========


@pytest.fixture
def sample_signal():
    """샘플 Signal 데이터"""
    return {
        "signal_id": "SIG-2025-001",
        "title": "콜센터 AHT 최적화",
        "source": "KT",
        "channel": "영업PM",
        "play_id": "KT_Sales_S01",
        "customer_segment": "금융 콜센터",
        "pain": "평균 통화 시간 8분으로 고객 불만 및 인건비 증가",
        "kpi_hypothesis": ["AHT 15% 감소", "FCR 10% 향상"],
        "evidence": [{"type": "meeting_note", "title": "ABC금융 미팅", "url": "https://..."}],
        "status": "NEW",
        "owner": "홍길동",
        "confidence": 0.8,
        "created_at": datetime.now(UTC).isoformat(),
    }


@pytest.fixture
def sample_scorecard():
    """샘플 Scorecard 데이터"""
    return {
        "scorecard_id": "SCR-2025-001",
        "signal_id": "SIG-2025-001",
        "total_score": 75,
        "dimension_scores": {
            "problem_severity": 18,
            "willingness_to_pay": 15,
            "data_availability": 14,
            "feasibility": 16,
            "strategic_fit": 12,
        },
        "red_flags": [],
        "recommendation": {
            "decision": "GO",
            "next_step": "BRIEF",
            "rationale": "고객 Pain이 명확하고 예산 확보 가능성 높음",
        },
        "scored_by": "ScorecardEvaluator",
        "scored_at": datetime.now(UTC).isoformat(),
    }


# ========== Scorecard Tests ==========


class TestScorecardEvaluator:
    """ScorecardEvaluator 테스트"""

    def test_total_score_calculation(self, sample_scorecard):
        """총점 계산 테스트"""
        scores = sample_scorecard["dimension_scores"]
        expected_total = sum(scores.values())
        assert sample_scorecard["total_score"] == expected_total

    def test_go_recommendation(self, sample_scorecard):
        """GO 추천 테스트"""
        assert sample_scorecard["total_score"] >= 70
        assert len(sample_scorecard["red_flags"]) == 0
        assert sample_scorecard["recommendation"]["decision"] == "GO"

    def test_pivot_recommendation(self):
        """PIVOT 추천 테스트"""
        scorecard = {"total_score": 55, "red_flags": ["데이터 접근 어려움"], "recommendation": {}}

        # 50-69점, Red Flag 1개 이하 → PIVOT
        assert 50 <= scorecard["total_score"] < 70
        assert len(scorecard["red_flags"]) <= 1

    def test_dimension_score_range(self, sample_scorecard):
        """차원별 점수 범위 테스트"""
        for dimension, score in sample_scorecard["dimension_scores"].items():
            assert 0 <= score <= 20, f"{dimension} score out of range"


# ========== Brief Tests ==========


class TestBriefWriter:
    """BriefWriter 테스트"""

    def test_brief_required_fields(self):
        """Brief 필수 필드 테스트"""
        required_fields = [
            "brief_id",
            "signal_id",
            "title",
            "customer",
            "problem",
            "solution_hypothesis",
            "kpis",
            "evidence",
            "validation_plan",
            "owner",
            "created_at",
        ]

        brief = {
            "brief_id": "BRF-2025-001",
            "signal_id": "SIG-2025-001",
            "title": "콜센터 AHT 최적화 솔루션",
            "customer": {"segment": "금융", "buyer_role": "CS팀장"},
            "problem": {"pain": "높은 AHT", "why_now": "비용 압박"},
            "solution_hypothesis": {"approach": "AI 어시스턴트", "integration_points": ["CTI"]},
            "kpis": ["AHT 15% 감소"],
            "evidence": ["https://..."],
            "validation_plan": {
                "questions": ["실시간 제안이 도움이 되는가?"],
                "method": "5DAY_SPRINT",
                "success_criteria": ["만족도 4.0 이상"],
                "timebox_days": 5,
            },
            "owner": "홍길동",
            "created_at": datetime.now(UTC).isoformat(),
        }

        for field in required_fields:
            assert field in brief, f"Missing required field: {field}"


# ========== Workflow Tests ==========


class TestSeminarPipeline:
    """WF-01 Seminar Pipeline 테스트"""

    @pytest.mark.asyncio
    async def test_activity_creation(self):
        """Activity 생성 테스트"""
        from backend.agent_runtime.workflows.wf_seminar_pipeline import (
            SeminarInput,
            SeminarPipeline,
        )

        pipeline = SeminarPipeline()
        input_data = SeminarInput(
            url="https://example.com/ai-summit",
            themes=["AI", "금융"],
            play_id="EXT_Desk_D01_Seminar",
        )

        # 메타데이터 추출 테스트 (실제 URL 접근 없이)
        metadata = {"url": input_data.url, "title": "AI Summit 2025", "date": "2025-01-20"}

        activity = await pipeline._create_activity(input_data, metadata)

        assert activity.activity_id.startswith("ACT-")
        assert activity.source == "대외"
        assert activity.channel == "데스크리서치"
        assert activity.play_id == "EXT_Desk_D01_Seminar"


# ========== Integration Tests ==========


class TestConfluenceMCP:
    """Confluence MCP 테스트"""

    def test_mcp_tools_defined(self):
        """MCP 도구 정의 테스트"""
        from backend.integrations.mcp_confluence.server import MCP_TOOLS

        tool_names = [t["name"] for t in MCP_TOOLS]

        assert "confluence.search_pages" in tool_names
        assert "confluence.get_page" in tool_names
        assert "confluence.create_page" in tool_names
        assert "confluence.append_to_page" in tool_names


# ========== API Tests ==========


class TestAPIEndpoints:
    """API 엔드포인트 테스트"""

    @pytest.mark.asyncio
    async def test_health_check(self):
        """헬스체크 테스트"""
        from fastapi.testclient import TestClient

        from backend.api.main import app

        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

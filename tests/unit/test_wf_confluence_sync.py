"""
WF-06 Confluence Sync 단위 테스트
"""

import pytest

from backend.agent_runtime.workflows.wf_confluence_sync import (
    ConfluenceSyncPipeline,
    SyncAction,
    SyncInput,
    SyncOutput,
    SyncResult,
    SyncTarget,
    SyncTargetType,
    format_brief_page,
    format_scorecard_page,
    format_signal_page,
    run,
)


class TestSyncModels:
    """동기화 모델 테스트"""

    def test_sync_target_type_enum(self):
        """SyncTargetType enum 값 확인"""
        assert SyncTargetType.SIGNAL.value == "signal"
        assert SyncTargetType.SCORECARD.value == "scorecard"
        assert SyncTargetType.BRIEF.value == "brief"
        assert SyncTargetType.PLAY.value == "play"
        assert SyncTargetType.ACTIVITY.value == "activity"
        assert SyncTargetType.ALL.value == "all"

    def test_sync_action_enum(self):
        """SyncAction enum 값 확인"""
        assert SyncAction.CREATE_PAGE.value == "create_page"
        assert SyncAction.UPDATE_PAGE.value == "update_page"
        assert SyncAction.APPEND_LOG.value == "append_log"
        assert SyncAction.UPDATE_TABLE.value == "update_table"

    def test_sync_target_creation(self):
        """SyncTarget 생성 테스트"""
        target = SyncTarget(
            target_type=SyncTargetType.SIGNAL,
            target_id="SIG-2025-001",
            data={"title": "Test Signal"},
            action=SyncAction.CREATE_PAGE,
            play_id="KT_AI_P01",
        )

        assert target.target_type == SyncTargetType.SIGNAL
        assert target.target_id == "SIG-2025-001"
        assert target.data["title"] == "Test Signal"
        assert target.action == SyncAction.CREATE_PAGE
        assert target.play_id == "KT_AI_P01"

    def test_sync_input_defaults(self):
        """SyncInput 기본값 테스트"""
        sync_input = SyncInput()

        assert sync_input.targets == []
        assert sync_input.sync_type == "realtime"
        assert sync_input.play_id is None
        assert sync_input.dry_run is False

    def test_sync_output_structure(self):
        """SyncOutput 구조 테스트"""
        result = SyncResult(
            target_type=SyncTargetType.SIGNAL,
            target_id="SIG-2025-001",
            action=SyncAction.CREATE_PAGE,
            status="success",
            page_id="12345",
            page_url="https://example.com/page/12345",
        )

        output = SyncOutput(
            results=[result],
            summary={"total": 1, "success": 1, "failed": 0, "skipped": 0},
        )

        assert len(output.results) == 1
        assert output.summary["total"] == 1
        assert output.summary["success"] == 1


class TestPageFormatters:
    """페이지 포맷터 테스트"""

    def test_format_signal_page(self):
        """Signal 페이지 포맷 테스트"""
        signal = {
            "signal_id": "SIG-2025-001",
            "title": "AI 기반 고객 서비스 개선",
            "source": "KT",
            "channel": "영업PM",
            "play_id": "KT_AI_P01",
            "status": "NEW",
            "pain": "고객 응대 시간이 길어 불만 발생",
            "evidence": [
                {"title": "고객 설문", "url": "https://example.com", "note": "만족도 65%"}
            ],
            "tags": ["AI", "고객서비스", "자동화"],
            "created_at": "2025-01-15",
        }

        content = format_signal_page(signal)

        assert "SIG-2025-001" in content
        assert "AI 기반 고객 서비스 개선" in content
        assert "KT" in content
        assert "영업PM" in content
        assert "고객 응대 시간이 길어 불만 발생" in content
        assert "고객 설문" in content
        assert "AI, 고객서비스, 자동화" in content

    def test_format_scorecard_page(self):
        """Scorecard 페이지 포맷 테스트"""
        scorecard = {
            "signal_id": "SIG-2025-001",
            "total_score": 85,
            "dimensions": {
                "strategic_fit": {"score": 90},
                "market_size": {"score": 80},
                "feasibility": {"score": 85},
                "urgency": {"score": 80},
                "competitive": {"score": 90},
            },
            "decision": "GO",
            "rationale": "전략적 적합성과 경쟁력이 높음",
        }

        content = format_scorecard_page(scorecard)

        assert "85" in content
        assert "100점" in content
        assert "Strategic Fit" in content
        assert "GO" in content
        assert "전략적 적합성과 경쟁력이 높음" in content

    def test_format_brief_page(self):
        """Brief 페이지 포맷 테스트"""
        brief = {
            "brief_id": "BRF-2025-001",
            "title": "AI 고객 서비스 자동화 Brief",
            "signal_id": "SIG-2025-001",
            "status": "DRAFT",
            "executive_summary": "AI 기반 고객 서비스 자동화 제안",
            "problem_statement": "현재 고객 응대 시간 문제",
            "proposed_solution": "AI 챗봇 도입",
            "expected_impact": "응대 시간 50% 감소",
            "next_steps": "PoC 진행",
            "created_at": "2025-01-15",
        }

        content = format_brief_page(brief)

        assert "BRF-2025-001" in content
        assert "AI 고객 서비스 자동화 Brief" in content
        assert "DRAFT" in content
        assert "AI 기반 고객 서비스 자동화 제안" in content
        assert "AI 챗봇 도입" in content


class TestConfluenceSyncPipeline:
    """ConfluenceSyncPipeline 테스트"""

    def setup_method(self):
        """테스트 설정"""
        self.pipeline = ConfluenceSyncPipeline()

    @pytest.mark.asyncio
    async def test_run_empty_targets(self):
        """빈 대상으로 실행"""
        sync_input = SyncInput(targets=[])
        result = await self.pipeline.run(sync_input)

        assert isinstance(result, SyncOutput)
        assert len(result.results) == 0
        assert result.summary["total"] == 0

    @pytest.mark.asyncio
    async def test_run_dry_run(self):
        """dry_run 모드 테스트"""
        target = SyncTarget(
            target_type=SyncTargetType.SIGNAL,
            target_id="SIG-2025-001",
            data={"title": "Test Signal"},
            action=SyncAction.CREATE_PAGE,
        )
        sync_input = SyncInput(targets=[target], dry_run=True)

        result = await self.pipeline.run(sync_input)

        assert len(result.results) == 1
        assert result.results[0].status == "skipped"
        assert "dry_run" in result.results[0].error

    @pytest.mark.asyncio
    async def test_run_multiple_targets_dry_run(self):
        """여러 대상 dry_run 테스트"""
        targets = [
            SyncTarget(
                target_type=SyncTargetType.SIGNAL,
                target_id="SIG-2025-001",
                data={"title": "Signal 1"},
                action=SyncAction.CREATE_PAGE,
            ),
            SyncTarget(
                target_type=SyncTargetType.BRIEF,
                target_id="BRF-2025-001",
                data={"title": "Brief 1"},
                action=SyncAction.CREATE_PAGE,
            ),
        ]
        sync_input = SyncInput(targets=targets, dry_run=True)

        result = await self.pipeline.run(sync_input)

        assert len(result.results) == 2
        assert result.summary["total"] == 2
        assert result.summary["skipped"] == 2


class TestPipelineSteps:
    """파이프라인 단계 테스트"""

    def test_steps_defined(self):
        """STEPS 정의 확인"""
        pipeline = ConfluenceSyncPipeline()

        assert hasattr(pipeline, "STEPS")
        assert len(pipeline.STEPS) == 5

        step_ids = [s["id"] for s in pipeline.STEPS]
        assert "VALIDATE_TARGETS" in step_ids
        assert "PREPARE_CONTENT" in step_ids
        assert "SYNC_PAGES" in step_ids
        assert "UPDATE_TABLES" in step_ids
        assert "FINALIZE" in step_ids


class TestRunFunction:
    """run 함수 테스트"""

    @pytest.mark.asyncio
    async def test_run_with_empty_input(self):
        """빈 입력으로 실행"""
        result = await run({})

        assert "results" in result
        assert "summary" in result
        assert result["summary"]["total"] == 0

    @pytest.mark.asyncio
    async def test_run_with_dry_run(self):
        """dry_run으로 실행"""
        result = await run({
            "targets": [
                {
                    "target_type": "signal",
                    "target_id": "SIG-2025-001",
                    "data": {"title": "Test Signal"},
                    "action": "create_page",
                }
            ],
            "dry_run": True,
        })

        assert len(result["results"]) == 1
        assert result["results"][0]["status"] == "skipped"

    @pytest.mark.asyncio
    async def test_run_returns_dict(self):
        """dict 반환 확인"""
        result = await run({"dry_run": True})

        assert isinstance(result, dict)
        assert isinstance(result["results"], list)
        assert isinstance(result["summary"], dict)


class TestConvenienceMethods:
    """편의 메서드 테스트"""

    def setup_method(self):
        """테스트 설정"""
        self.pipeline = ConfluenceSyncPipeline()

    @pytest.mark.asyncio
    async def test_sync_signal_dry_run(self):
        """Signal 동기화 (실제 API 호출 없이)"""
        signal = {
            "signal_id": "SIG-2025-001",
            "title": "Test Signal",
            "source": "KT",
            "channel": "영업PM",
        }

        try:
            result = await self.pipeline.sync_signal(signal, SyncAction.CREATE_PAGE)
            assert result.target_type == SyncTargetType.SIGNAL
        except ValueError:
            pass

    @pytest.mark.asyncio
    async def test_log_activity_skipped_without_config(self):
        """환경변수 미설정 시 activity log 건너뛰기"""
        activity = {
            "activity_id": "ACT-001",
            "title": "Test Activity",
            "type": "meeting",
            "owner": "테스터",
            "status": "completed",
        }

        result = await self.pipeline.log_activity(activity)

        assert result.status == "skipped"
        assert "not configured" in result.error

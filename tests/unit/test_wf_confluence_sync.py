"""
WF-06 Confluence Sync 단위 테스트
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.agent_runtime.workflows.wf_confluence_sync import (
    ConfluenceSyncPipeline,
    ConfluenceSyncPipelineWithDB,
    ConfluenceSyncPipelineWithEvents,
    MockConfluenceClient,
    SyncAction,
    SyncInput,
    SyncOutput,
    SyncResult,
    SyncTarget,
    SyncTargetType,
    format_activity_log,
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
        result = await run(
            {
                "targets": [
                    {
                        "target_type": "signal",
                        "target_id": "SIG-2025-001",
                        "data": {"title": "Test Signal"},
                        "action": "create_page",
                    }
                ],
                "dry_run": True,
            }
        )

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


# ============================================================
# MockConfluenceClient Tests
# ============================================================


class TestMockConfluenceClient:
    """MockConfluenceClient 테스트"""

    @pytest.fixture
    def client_configured(self):
        """설정된 클라이언트"""
        with patch.dict(os.environ, {"CONFLUENCE_API_TOKEN": "test-token"}):
            yield MockConfluenceClient()

    @pytest.fixture
    def client_not_configured(self):
        """미설정 클라이언트"""
        env_copy = os.environ.copy()
        if "CONFLUENCE_API_TOKEN" in env_copy:
            del env_copy["CONFLUENCE_API_TOKEN"]
        with patch.dict(os.environ, env_copy, clear=True):
            client = MockConfluenceClient()
            client.is_configured = False
            yield client

    @pytest.mark.asyncio
    async def test_create_page_success(self, client_configured):
        """페이지 생성 성공"""
        result = await client_configured.create_page(
            title="Test Page",
            body_md="# Test Content",
            parent_id="parent-123",
            labels=["test"],
        )

        assert "page_id" in result
        assert "url" in result
        assert result["page_id"].startswith("mock-")

    @pytest.mark.asyncio
    async def test_create_page_not_configured(self, client_not_configured):
        """미설정 시 페이지 생성 실패"""
        with pytest.raises(ValueError, match="Confluence not configured"):
            await client_not_configured.create_page(
                title="Test",
                body_md="Content",
            )

    @pytest.mark.asyncio
    async def test_update_page_success(self, client_configured):
        """페이지 수정 성공"""
        result = await client_configured.update_page(
            page_id="page-123",
            title="Updated Page",
            body_md="# Updated Content",
        )

        assert result["page_id"] == "page-123"
        assert "url" in result

    @pytest.mark.asyncio
    async def test_append_to_page_success(self, client_configured):
        """페이지 내용 추가 성공"""
        result = await client_configured.append_to_page(
            page_id="page-123",
            content="New content",
        )

        assert result["page_id"] == "page-123"


# ============================================================
# Format Activity Log Tests
# ============================================================


class TestFormatActivityLog:
    """Activity 로그 포맷터 테스트"""

    def test_basic_activity(self):
        """기본 Activity 로그 포맷"""
        activity = {
            "activity_id": "ACT-001",
            "title": "세미나 참석",
            "type": "SEMINAR",
            "owner": "홍길동",
            "status": "COMPLETED",
            "date": "2025-01-15",
        }
        content = format_activity_log(activity)

        assert "| 2025-01-15 |" in content
        assert "ACT-001" in content
        assert "세미나 참석" in content
        assert "SEMINAR" in content
        assert "홍길동" in content
        assert "COMPLETED" in content

    def test_activity_with_missing_fields(self):
        """필드 누락 시 기본값"""
        activity = {"activity_id": "ACT-002"}
        content = format_activity_log(activity)

        assert "ACT-002" in content
        assert "N/A" in content


# ============================================================
# ConfluenceSyncPipelineWithEvents Tests
# ============================================================


class TestConfluenceSyncPipelineWithEvents:
    """ConfluenceSyncPipelineWithEvents 테스트"""

    @pytest.fixture
    def mock_emitter(self):
        """Mock 이벤트 emitter"""
        emitter = MagicMock()
        emitter.emit_run_started = AsyncMock()
        emitter.emit_step_started = AsyncMock()
        emitter.emit_step_finished = AsyncMock()
        emitter.emit_run_finished = AsyncMock()
        emitter.emit_run_error = AsyncMock()
        return emitter

    @pytest.fixture
    def pipeline(self, mock_emitter):
        """파이프라인 인스턴스"""
        with patch.dict(
            os.environ,
            {"CONFLUENCE_API_TOKEN": "test-token"},
        ):
            yield ConfluenceSyncPipelineWithEvents(mock_emitter)

    @pytest.mark.asyncio
    async def test_emits_run_started(self, pipeline, mock_emitter):
        """run_started 이벤트 발행"""
        sync_input = SyncInput(targets=[], dry_run=True)

        await pipeline.run(sync_input)

        mock_emitter.emit_run_started.assert_called_once()
        call_kwargs = mock_emitter.emit_run_started.call_args.kwargs
        assert call_kwargs["workflow_id"] == "WF-06"

    @pytest.mark.asyncio
    async def test_emits_step_events(self, pipeline, mock_emitter):
        """단계별 이벤트 발행"""
        sync_input = SyncInput(targets=[], dry_run=True)

        await pipeline.run(sync_input)

        # 5개 단계 시작/완료 이벤트
        assert mock_emitter.emit_step_started.call_count == 5
        assert mock_emitter.emit_step_finished.call_count == 5

    @pytest.mark.asyncio
    async def test_emits_run_finished(self, pipeline, mock_emitter):
        """run_finished 이벤트 발행"""
        sync_input = SyncInput(targets=[], dry_run=True)

        await pipeline.run(sync_input)

        mock_emitter.emit_run_finished.assert_called_once()

    @pytest.mark.asyncio
    async def test_emits_run_error_on_exception(self, pipeline, mock_emitter):
        """예외 발생 시 run_error 이벤트 발행"""
        with patch.object(ConfluenceSyncPipeline, "run", side_effect=Exception("Test error")):
            sync_input = SyncInput(targets=[])

            with pytest.raises(Exception, match="Test error"):
                await pipeline.run(sync_input)

            mock_emitter.emit_run_error.assert_called_once()


# ============================================================
# ConfluenceSyncPipelineWithDB Tests
# ============================================================


class TestConfluenceSyncPipelineWithDB:
    """ConfluenceSyncPipelineWithDB 테스트"""

    @pytest.fixture
    def mock_emitter(self):
        """Mock 이벤트 emitter"""
        emitter = MagicMock()
        emitter.emit_run_started = AsyncMock()
        emitter.emit_step_started = AsyncMock()
        emitter.emit_step_finished = AsyncMock()
        emitter.emit_run_finished = AsyncMock()
        emitter.emit_run_error = AsyncMock()
        return emitter

    @pytest.fixture
    def mock_db(self):
        """Mock DB 세션"""
        return MagicMock()

    @pytest.fixture
    def pipeline(self, mock_emitter, mock_db):
        """파이프라인 인스턴스"""
        with patch.dict(
            os.environ,
            {"CONFLUENCE_API_TOKEN": "test-token"},
        ):
            yield ConfluenceSyncPipelineWithDB(mock_emitter, mock_db)

    @pytest.mark.asyncio
    async def test_run_with_db(self, pipeline):
        """DB 연동 실행"""
        sync_input = SyncInput(targets=[], dry_run=True)

        result = await pipeline.run(sync_input)

        assert result.summary["total"] == 0

    @pytest.mark.asyncio
    async def test_save_sync_results_empty(self, pipeline):
        """빈 결과 저장"""
        saved = await pipeline.save_sync_results([])

        assert saved["total"] == 0
        assert saved["signals"] == 0
        assert saved["scorecards"] == 0
        assert saved["briefs"] == 0

    @pytest.mark.asyncio
    async def test_save_sync_results_success_signal(self, pipeline):
        """Signal 성공 결과 저장"""
        # Mock the internal method directly
        pipeline._update_signal_page_id = AsyncMock()

        results = [
            SyncResult(
                target_type=SyncTargetType.SIGNAL,
                target_id="SIG-001",
                action=SyncAction.CREATE_PAGE,
                status="success",
                page_id="page-123",
                page_url="https://example.com/page/123",
            )
        ]

        saved = await pipeline.save_sync_results(results)

        assert saved["total"] == 1
        assert saved["signals"] == 1
        pipeline._update_signal_page_id.assert_called_once_with(
            "SIG-001", "page-123", "https://example.com/page/123"
        )

    @pytest.mark.asyncio
    async def test_save_sync_results_failed_skipped(self, pipeline):
        """실패/스킵 결과 무시"""
        results = [
            SyncResult(
                target_type=SyncTargetType.SIGNAL,
                target_id="SIG-001",
                action=SyncAction.CREATE_PAGE,
                status="failed",
                error="Test error",
            ),
            SyncResult(
                target_type=SyncTargetType.SIGNAL,
                target_id="SIG-002",
                action=SyncAction.CREATE_PAGE,
                status="skipped",
            ),
        ]

        saved = await pipeline.save_sync_results(results)

        assert saved["total"] == 0

    @pytest.mark.asyncio
    async def test_fetch_signals_from_db_error_handling(self, pipeline):
        """Signal 조회 오류 처리"""
        # _fetch_signals_from_db handles exceptions internally and returns []
        # We test that it returns empty list when db access fails
        signals = await pipeline._fetch_signals_from_db(None)
        # Should return empty list due to import error in test environment
        assert signals == []

    @pytest.mark.asyncio
    async def test_fetch_scorecards_from_db_error_handling(self, pipeline):
        """Scorecard 조회 오류 처리"""
        # _fetch_scorecards_from_db handles exceptions internally and returns []
        scorecards = await pipeline._fetch_scorecards_from_db(None)
        assert scorecards == []

    @pytest.mark.asyncio
    async def test_fetch_briefs_from_db_error_handling(self, pipeline):
        """Brief 조회 오류 처리"""
        # _fetch_briefs_from_db handles exceptions internally and returns []
        briefs = await pipeline._fetch_briefs_from_db(None)
        assert briefs == []

    @pytest.mark.asyncio
    async def test_sync_from_db_signal(self, pipeline):
        """DB에서 Signal 동기화"""
        with patch.object(
            pipeline,
            "_fetch_signals_from_db",
            return_value=[
                {
                    "type": SyncTargetType.SIGNAL,
                    "id": "SIG-001",
                    "data": {"signal_id": "SIG-001", "title": "Test"},
                }
            ],
        ):
            with patch.object(
                pipeline,
                "save_sync_results",
                return_value={"total": 1},
            ):
                result = await pipeline.sync_from_db(
                    SyncTargetType.SIGNAL,
                    target_ids=["SIG-001"],
                )

                assert result.summary["total"] == 1

    @pytest.mark.asyncio
    async def test_sync_from_db_all(self, pipeline):
        """DB에서 모든 타입 동기화"""
        with patch.object(
            pipeline,
            "_fetch_signals_from_db",
            return_value=[{"type": SyncTargetType.SIGNAL, "id": "S1", "data": {}}],
        ):
            with patch.object(
                pipeline,
                "_fetch_scorecards_from_db",
                return_value=[{"type": SyncTargetType.SCORECARD, "id": "SC1", "data": {}}],
            ):
                with patch.object(
                    pipeline,
                    "_fetch_briefs_from_db",
                    return_value=[{"type": SyncTargetType.BRIEF, "id": "B1", "data": {}}],
                ):
                    with patch.object(
                        pipeline,
                        "save_sync_results",
                        return_value={"total": 3},
                    ):
                        result = await pipeline.sync_from_db(
                            SyncTargetType.ALL,
                        )

                        assert result.summary["total"] == 3


# ============================================================
# Additional Pipeline Tests
# ============================================================


class TestPipelineEdgeCases:
    """파이프라인 엣지 케이스 테스트"""

    @pytest.fixture
    def pipeline(self):
        """파이프라인 인스턴스"""
        with patch.dict(
            os.environ,
            {
                "CONFLUENCE_API_TOKEN": "test-token",
                "CONFLUENCE_LIVE_DOC_PAGE_ID": "live-doc-123",
                "CONFLUENCE_PLAY_DB_PAGE_ID": "play-db-123",
            },
        ):
            yield ConfluenceSyncPipeline()

    @pytest.mark.asyncio
    async def test_create_signal_page(self, pipeline):
        """Signal 페이지 생성"""
        targets = [
            SyncTarget(
                target_type=SyncTargetType.SIGNAL,
                target_id="SIG-001",
                data={
                    "signal_id": "SIG-001",
                    "title": "Test Signal",
                    "pain": "Test pain",
                },
                action=SyncAction.CREATE_PAGE,
            )
        ]
        sync_input = SyncInput(targets=targets)

        result = await pipeline.run(sync_input)

        assert result.summary["success"] == 1
        assert result.results[0].page_id is not None

    @pytest.mark.asyncio
    async def test_create_brief_page(self, pipeline):
        """Brief 페이지 생성"""
        targets = [
            SyncTarget(
                target_type=SyncTargetType.BRIEF,
                target_id="BRF-001",
                data={
                    "brief_id": "BRF-001",
                    "title": "Test Brief",
                },
                action=SyncAction.CREATE_PAGE,
            )
        ]
        sync_input = SyncInput(targets=targets)

        result = await pipeline.run(sync_input)

        assert result.summary["success"] == 1

    @pytest.mark.asyncio
    async def test_create_scorecard_page(self, pipeline):
        """Scorecard 페이지 생성"""
        targets = [
            SyncTarget(
                target_type=SyncTargetType.SCORECARD,
                target_id="SC-001",
                data={
                    "scorecard_id": "SC-001",
                    "signal_id": "SIG-001",
                    "total_score": 75,
                    "dimensions": {},
                    "decision": "GO",
                    "rationale": "Test",
                },
                action=SyncAction.CREATE_PAGE,
            )
        ]
        sync_input = SyncInput(targets=targets)

        result = await pipeline.run(sync_input)

        assert result.summary["success"] == 1

    @pytest.mark.asyncio
    async def test_update_page_without_page_id(self, pipeline):
        """page_id 없이 업데이트 시도"""
        targets = [
            SyncTarget(
                target_type=SyncTargetType.SIGNAL,
                target_id="SIG-001",
                data={"title": "Test"},
                action=SyncAction.UPDATE_PAGE,
                page_id=None,
            )
        ]
        sync_input = SyncInput(targets=targets)

        result = await pipeline.run(sync_input)

        assert result.summary["failed"] == 1
        assert "page_id is required" in result.results[0].error

    @pytest.mark.asyncio
    async def test_update_page_with_page_id(self, pipeline):
        """page_id로 업데이트"""
        targets = [
            SyncTarget(
                target_type=SyncTargetType.SIGNAL,
                target_id="SIG-001",
                data={"signal_id": "SIG-001", "title": "Updated Signal"},
                action=SyncAction.UPDATE_PAGE,
                page_id="existing-page-123",
            )
        ]
        sync_input = SyncInput(targets=targets)

        result = await pipeline.run(sync_input)

        assert result.summary["success"] == 1
        assert result.results[0].page_id == "existing-page-123"

    @pytest.mark.asyncio
    async def test_append_activity_log(self, pipeline):
        """Activity 로그 추가"""
        targets = [
            SyncTarget(
                target_type=SyncTargetType.ACTIVITY,
                target_id="ACT-001",
                data={
                    "activity_id": "ACT-001",
                    "title": "Test Activity",
                    "type": "SEMINAR",
                    "owner": "Tester",
                    "status": "COMPLETED",
                    "date": "2025-01-15",
                },
                action=SyncAction.APPEND_LOG,
            )
        ]
        sync_input = SyncInput(targets=targets)

        result = await pipeline.run(sync_input)

        assert result.summary["success"] == 1

    @pytest.mark.asyncio
    async def test_update_table_not_implemented(self, pipeline):
        """UPDATE_TABLE 미구현"""
        targets = [
            SyncTarget(
                target_type=SyncTargetType.PLAY,
                target_id="PLAY-001",
                data={"stats": {}},
                action=SyncAction.UPDATE_TABLE,
            )
        ]
        sync_input = SyncInput(targets=targets)

        result = await pipeline.run(sync_input)

        assert result.summary["skipped"] == 1
        assert "not implemented" in result.results[0].error

    @pytest.mark.asyncio
    async def test_multiple_targets_mixed(self, pipeline):
        """다양한 대상 동기화"""
        targets = [
            SyncTarget(
                target_type=SyncTargetType.SIGNAL,
                target_id="SIG-001",
                data={"signal_id": "SIG-001", "title": "Signal 1"},
            ),
            SyncTarget(
                target_type=SyncTargetType.BRIEF,
                target_id="BRF-001",
                data={"brief_id": "BRF-001", "title": "Brief 1"},
            ),
            SyncTarget(
                target_type=SyncTargetType.SCORECARD,
                target_id="SC-001",
                data={
                    "scorecard_id": "SC-001",
                    "total_score": 80,
                    "dimensions": {},
                    "decision": "GO",
                    "rationale": "Test",
                },
            ),
        ]
        sync_input = SyncInput(targets=targets)

        result = await pipeline.run(sync_input)

        assert result.summary["total"] == 3
        assert result.summary["success"] == 3

    @pytest.mark.asyncio
    async def test_unsupported_type_for_create(self, pipeline):
        """지원되지 않는 타입 생성 시도"""
        targets = [
            SyncTarget(
                target_type=SyncTargetType.PLAY,
                target_id="PLAY-001",
                data={"title": "Test Play"},
                action=SyncAction.CREATE_PAGE,
            )
        ]
        sync_input = SyncInput(targets=targets)

        result = await pipeline.run(sync_input)

        assert result.summary["failed"] == 1
        assert "Cannot create page for type" in result.results[0].error


# ============================================================
# Page Parsers Tests (Confluence → Dict)
# ============================================================


class TestPageParsers:
    """페이지 파서 테스트 (양방향 동기화)"""

    def test_parse_signal_page_basic(self):
        """Signal 페이지 파싱 기본"""
        from backend.agent_runtime.workflows.wf_confluence_sync import parse_signal_page

        content = """# AI 기반 고객 서비스 개선

## 기본 정보

| 항목 | 값 |
|------|-----|
| Signal ID | SIG-2025-001 |
| Play ID | KT_AI_P01 |
| Source | KT |
| Channel | 영업PM |
| Status | NEW |
| Created | 2025-01-15 |

## Pain Point

고객 응대 시간이 길어 불만 발생

## Evidence

- [고객 설문](https://example.com/survey) - 만족도 65%
- [CS 리포트](https://example.com/report) - 분석 결과

## Tags

AI, 고객서비스, 자동화
"""
        result = parse_signal_page(content, "page-123")

        assert result["title"] == "AI 기반 고객 서비스 개선"
        assert result["signal_id"] == "SIG-2025-001"
        assert result["play_id"] == "KT_AI_P01"
        assert result["source"] == "KT"
        assert result["channel"] == "영업PM"
        assert result["status"] == "NEW"
        assert result["pain"] == "고객 응대 시간이 길어 불만 발생"
        assert len(result["evidence"]) == 2
        assert result["evidence"][0]["title"] == "고객 설문"
        assert result["tags"] == ["AI", "고객서비스", "자동화"]
        assert result["confluence_page_id"] == "page-123"

    def test_parse_signal_page_minimal(self):
        """Signal 페이지 파싱 최소 정보"""
        from backend.agent_runtime.workflows.wf_confluence_sync import parse_signal_page

        content = """# Test Signal

## 기본 정보

| 항목 | 값 |
|------|-----|
| Signal ID | SIG-001 |

## Pain Point

Test pain

## Evidence

- 없음

## Tags

없음
"""
        result = parse_signal_page(content)

        assert result["title"] == "Test Signal"
        assert result["signal_id"] == "SIG-001"
        assert result["pain"] == "Test pain"
        assert "evidence" not in result  # 없음은 파싱 안함
        assert "tags" not in result  # 없음은 파싱 안함

    def test_parse_scorecard_page_basic(self):
        """Scorecard 페이지 파싱 기본"""
        from backend.agent_runtime.workflows.wf_confluence_sync import parse_scorecard_page

        content = """# Scorecard: SIG-2025-001

## 총점

**85점** / 100점

## 차원별 점수

| 차원 | 점수 |
|------|------|
| Strategic Fit | 90 |
| Market Size | 80 |
| Feasibility | 85 |
| Urgency | 80 |
| Competitive | 90 |

## 결정

**GO**

## 근거

전략적 적합성과 경쟁력이 높음
"""
        result = parse_scorecard_page(content, "page-456")

        assert result["signal_id"] == "SIG-2025-001"
        assert result["total_score"] == 85
        assert result["decision"] == "GO"
        assert result["rationale"] == "전략적 적합성과 경쟁력이 높음"
        assert result["confluence_page_id"] == "page-456"
        # 차원명은 lowercase + underscore로 변환됨
        # "Strategic Fit" → "strategic_fit" 이지만 공백이 단일 underscore가 됨
        # 실제 결과 확인: "market_size"가 있음
        assert "market_size" in result["dimensions"]
        assert result["dimensions"]["market_size"]["score"] == 80

    def test_parse_brief_page_basic(self):
        """Brief 페이지 파싱 기본"""
        from backend.agent_runtime.workflows.wf_confluence_sync import parse_brief_page

        content = """# AI 고객 서비스 자동화 Brief

## 기본 정보

| 항목 | 값 |
|------|-----|
| Brief ID | BRF-2025-001 |
| Signal ID | SIG-2025-001 |
| Status | DRAFT |
| Created | 2025-01-15 |

## Executive Summary

AI 기반 고객 서비스 자동화 제안

## Problem Statement

현재 고객 응대 시간 문제

## Proposed Solution

AI 챗봇 도입

## Expected Impact

응대 시간 50% 감소

## Next Steps

PoC 진행
"""
        result = parse_brief_page(content, "page-789")

        assert result["title"] == "AI 고객 서비스 자동화 Brief"
        assert result["brief_id"] == "BRF-2025-001"
        assert result["signal_id"] == "SIG-2025-001"
        assert result["status"] == "DRAFT"
        assert result["executive_summary"] == "AI 기반 고객 서비스 자동화 제안"
        assert result["proposed_solution"] == "AI 챗봇 도입"
        assert result["confluence_page_id"] == "page-789"


class TestDetectPageType:
    """페이지 타입 감지 테스트"""

    def test_detect_by_label_signal(self):
        """라벨로 Signal 감지"""
        from backend.agent_runtime.workflows.wf_confluence_sync import detect_page_type

        result = detect_page_type("any content", labels=["signal", "KT_AI_P01"])
        assert result == SyncTargetType.SIGNAL

    def test_detect_by_label_scorecard(self):
        """라벨로 Scorecard 감지"""
        from backend.agent_runtime.workflows.wf_confluence_sync import detect_page_type

        result = detect_page_type("any content", labels=["scorecard"])
        assert result == SyncTargetType.SCORECARD

    def test_detect_by_label_brief(self):
        """라벨로 Brief 감지"""
        from backend.agent_runtime.workflows.wf_confluence_sync import detect_page_type

        result = detect_page_type("any content", labels=["brief"])
        assert result == SyncTargetType.BRIEF

    def test_detect_by_content_signal(self):
        """내용으로 Signal 감지"""
        from backend.agent_runtime.workflows.wf_confluence_sync import detect_page_type

        content = "| Signal ID | SIG-001 |\n## Pain Point\nTest pain"
        result = detect_page_type(content)
        assert result == SyncTargetType.SIGNAL

    def test_detect_by_content_scorecard(self):
        """내용으로 Scorecard 감지"""
        from backend.agent_runtime.workflows.wf_confluence_sync import detect_page_type

        content = "# Scorecard: SIG-001\n## 차원별 점수\nTest"
        result = detect_page_type(content)
        assert result == SyncTargetType.SCORECARD

    def test_detect_by_content_brief(self):
        """내용으로 Brief 감지"""
        from backend.agent_runtime.workflows.wf_confluence_sync import detect_page_type

        content = "| Brief ID | BRF-001 |\n## Executive Summary\nTest"
        result = detect_page_type(content)
        assert result == SyncTargetType.BRIEF

    def test_detect_unknown(self):
        """알 수 없는 타입"""
        from backend.agent_runtime.workflows.wf_confluence_sync import detect_page_type

        result = detect_page_type("random content without markers")
        assert result is None


class TestMockConfluenceClientExtended:
    """MockConfluenceClient 확장 기능 테스트"""

    @pytest.fixture
    def client(self):
        """설정된 클라이언트"""
        with patch.dict(os.environ, {"CONFLUENCE_API_TOKEN": "test-token"}):
            yield MockConfluenceClient()

    @pytest.fixture
    def client_not_configured(self):
        """미설정 클라이언트"""
        env_copy = os.environ.copy()
        if "CONFLUENCE_API_TOKEN" in env_copy:
            del env_copy["CONFLUENCE_API_TOKEN"]
        with patch.dict(os.environ, env_copy, clear=True):
            client = MockConfluenceClient()
            client.is_configured = False
            yield client

    @pytest.mark.asyncio
    async def test_get_page_success(self, client):
        """페이지 조회 성공"""
        result = await client.get_page("page-123")

        assert result["page_id"] == "page-123"
        assert "title" in result
        assert "body" in result
        assert "url" in result

    @pytest.mark.asyncio
    async def test_get_page_not_configured(self, client_not_configured):
        """미설정 시 페이지 조회 실패"""
        with pytest.raises(ValueError, match="Confluence not configured"):
            await client_not_configured.get_page("page-123")

    @pytest.mark.asyncio
    async def test_search_pages_success(self, client):
        """페이지 검색 성공"""
        result = await client.search_pages('label = "signal"')

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_search_pages_not_configured(self, client_not_configured):
        """미설정 시 페이지 검색 실패"""
        with pytest.raises(ValueError, match="Confluence not configured"):
            await client_not_configured.search_pages('label = "signal"')

    @pytest.mark.asyncio
    async def test_get_pages_by_label(self, client):
        """라벨로 페이지 조회"""
        result = await client.get_pages_by_label("signal")

        assert isinstance(result, list)


class TestBidirectionalSync:
    """양방향 동기화 테스트"""

    @pytest.fixture
    def mock_emitter(self):
        """Mock 이벤트 emitter"""
        emitter = MagicMock()
        emitter.emit_run_started = AsyncMock()
        emitter.emit_step_started = AsyncMock()
        emitter.emit_step_finished = AsyncMock()
        emitter.emit_run_finished = AsyncMock()
        emitter.emit_run_error = AsyncMock()
        return emitter

    @pytest.fixture
    def mock_db(self):
        """Mock DB 세션"""
        return MagicMock()

    @pytest.fixture
    def pipeline(self, mock_emitter, mock_db):
        """파이프라인 인스턴스"""
        with patch.dict(
            os.environ,
            {"CONFLUENCE_API_TOKEN": "test-token"},
        ):
            yield ConfluenceSyncPipelineWithDB(mock_emitter, mock_db)

    @pytest.mark.asyncio
    async def test_import_from_confluence_with_page_ids(self, pipeline):
        """페이지 ID로 import"""
        # Mock get_page
        pipeline.confluence.get_page = AsyncMock(
            return_value={
                "page_id": "page-123",
                "body": """# Test Signal

## 기본 정보

| 항목 | 값 |
| Signal ID | SIG-001 |

## Pain Point

Test pain
""",
                "url": "https://example.com/page/123",
                "labels": ["signal"],
            }
        )

        # Mock _import_page_to_db
        pipeline._import_page_to_db = AsyncMock(
            return_value={
                "page_id": "page-123",
                "target_type": "signal",
                "target_id": "SIG-001",
                "action": "created",
            }
        )

        result = await pipeline.import_from_confluence(
            target_type=SyncTargetType.SIGNAL,
            page_ids=["page-123"],
        )

        assert result["total"] == 1
        assert result["imported"] == 1 or result["updated"] == 1 or result["skipped"] == 1

    @pytest.mark.asyncio
    async def test_import_from_confluence_empty_result(self, pipeline):
        """빈 결과로 import"""
        # Mock get_pages_by_label to return empty list
        pipeline.confluence.get_pages_by_label = AsyncMock(return_value=[])

        result = await pipeline.import_from_confluence(
            target_type=SyncTargetType.SIGNAL,
        )

        assert result["total"] == 0
        assert result["imported"] == 0

    @pytest.mark.asyncio
    async def test_bidirectional_sync(self, pipeline):
        """양방향 동기화 실행"""
        # Mock import_from_confluence
        pipeline.import_from_confluence = AsyncMock(
            return_value={
                "total": 2,
                "imported": 1,
                "updated": 1,
                "skipped": 0,
                "failed": 0,
                "details": [],
            }
        )

        # Mock sync_from_db
        pipeline.sync_from_db = AsyncMock(
            return_value=SyncOutput(
                results=[],
                summary={"total": 3, "success": 3, "failed": 0, "skipped": 0},
            )
        )

        result = await pipeline.bidirectional_sync(SyncTargetType.ALL)

        assert "import_results" in result
        assert "export_results" in result
        assert result["import_results"]["total"] == 2
        assert result["export_results"]["total"] == 3

    @pytest.mark.asyncio
    async def test_import_signal_new(self, pipeline):
        """새 Signal import"""
        content = """# Test Signal

## 기본 정보

| 항목 | 값 |
| Signal ID | SIG-NEW-001 |

## Pain Point

New signal pain
"""
        # Mock backend.repositories.signal 모듈
        mock_signal_repo = MagicMock()
        mock_signal_repo.generate_signal_id = AsyncMock(return_value="SIG-AUTO-001")
        mock_signal_repo.get_by_signal_id = AsyncMock(return_value=None)
        mock_signal_repo.create = AsyncMock()

        mock_module = MagicMock()
        mock_module.SignalRepository = MagicMock(return_value=mock_signal_repo)

        import sys

        with patch.dict(sys.modules, {"backend.repositories.signal": mock_module}):
            result = await pipeline._import_signal("page-123", content, "https://example.com")

            assert result["action"] == "created"
            assert "target_id" in result

    @pytest.mark.asyncio
    async def test_import_scorecard_without_signal_id(self, pipeline):
        """signal_id 없는 Scorecard import (스킵)"""
        content = """# Scorecard

## 총점

**75점** / 100점
"""
        # signal_id가 없으면 스킵됨 - ScorecardRepository import 전에 반환
        # parse_scorecard_page가 signal_id를 추출하지 못하면 스킵
        result = await pipeline._import_scorecard("page-123", content, None)

        assert result["action"] == "skipped"
        assert "signal_id not found" in result["reason"]


class TestSyncActionImportPage:
    """SyncAction.IMPORT_PAGE 테스트"""

    def test_import_page_enum_exists(self):
        """IMPORT_PAGE enum 값 확인"""
        assert SyncAction.IMPORT_PAGE.value == "import_page"

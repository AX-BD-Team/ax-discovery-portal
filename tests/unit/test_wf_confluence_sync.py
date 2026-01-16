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

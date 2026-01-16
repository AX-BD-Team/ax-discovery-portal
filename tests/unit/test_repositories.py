"""
Repositories 단위 테스트

테스트 대상:
- CRUDBase (base.py)
- SignalRepository (signal.py)
- ScorecardRepository (scorecard.py)
- BriefRepository (brief.py)
- PlayRecordRepository (play_record.py)
"""

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.database.models.brief import BriefStatus, OpportunityBrief
from backend.database.models.play_record import PlayRecord
from backend.database.models.scorecard import Scorecard
from backend.database.models.signal import Signal, SignalChannel, SignalSource, SignalStatus
from backend.database.repositories.base import CRUDBase
from backend.database.repositories.brief import BriefRepository, brief_repo
from backend.database.repositories.play_record import PlayRecordRepository, play_record_repo
from backend.database.repositories.scorecard import ScorecardRepository, scorecard_repo
from backend.database.repositories.signal import SignalRepository, signal_repo


# =============================================================================
# CRUDBase 테스트
# =============================================================================
class TestCRUDBase:
    """CRUDBase 단위 테스트 - select 패치 기반"""

    def setup_method(self):
        """테스트 설정"""
        self.mock_db = AsyncMock()
        self.mock_model = MagicMock()
        self.mock_model.id = MagicMock()  # SQLAlchemy 컬럼처럼 동작하도록
        self.crud = CRUDBase(self.mock_model)

    @pytest.mark.asyncio
    async def test_get_returns_item(self):
        """ID로 단일 레코드 조회 성공"""
        mock_obj = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_obj
        self.mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("backend.database.repositories.base.select") as mock_select:
            mock_select.return_value.where.return_value = MagicMock()
            result = await self.crud.get(self.mock_db, "test-id")

        assert result == mock_obj
        self.mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_returns_none_when_not_found(self):
        """ID로 조회 시 없으면 None 반환"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        self.mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("backend.database.repositories.base.select") as mock_select:
            mock_select.return_value.where.return_value = MagicMock()
            result = await self.crud.get(self.mock_db, "non-existent-id")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_multi_returns_list(self):
        """여러 레코드 조회 (페이지네이션)"""
        mock_items = [MagicMock(), MagicMock(), MagicMock()]
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_items
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        self.mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("backend.database.repositories.base.select") as mock_select:
            mock_select.return_value.offset.return_value.limit.return_value = MagicMock()
            result = await self.crud.get_multi(self.mock_db, skip=0, limit=10)

        assert result == mock_items
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_get_multi_with_pagination(self):
        """페이지네이션 파라미터 적용 확인"""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        self.mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("backend.database.repositories.base.select") as mock_select:
            mock_select.return_value.offset.return_value.limit.return_value = MagicMock()
            await self.crud.get_multi(self.mock_db, skip=10, limit=5)

        self.mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_count_returns_total(self):
        """전체 레코드 수 조회"""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 42
        self.mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("backend.database.repositories.base.select") as mock_select:
            mock_select.return_value.select_from.return_value = MagicMock()
            result = await self.crud.count(self.mock_db)

        assert result == 42

    @pytest.mark.asyncio
    async def test_count_returns_zero_when_empty(self):
        """빈 테이블일 때 0 반환"""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        self.mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("backend.database.repositories.base.select") as mock_select:
            mock_select.return_value.select_from.return_value = MagicMock()
            result = await self.crud.count(self.mock_db)

        assert result == 0

    @pytest.mark.asyncio
    async def test_create_success(self):
        """새 레코드 생성 성공"""
        mock_obj = MagicMock()
        self.mock_model.return_value = mock_obj
        self.mock_db.add = MagicMock()
        self.mock_db.flush = AsyncMock()
        self.mock_db.refresh = AsyncMock()

        obj_data = {"field1": "value1", "field2": "value2"}
        result = await self.crud.create(self.mock_db, obj_data)

        self.mock_db.add.assert_called_once()
        self.mock_db.flush.assert_called_once()
        assert result == mock_obj

    @pytest.mark.asyncio
    async def test_update_success(self):
        """레코드 업데이트 성공"""
        mock_obj = MagicMock()
        mock_obj.field1 = "old_value"
        mock_obj.field2 = "old_value2"
        self.mock_db.flush = AsyncMock()
        self.mock_db.refresh = AsyncMock()

        update_data = {"field1": "new_value", "field2": "new_value2"}
        result = await self.crud.update(self.mock_db, mock_obj, update_data)

        self.mock_db.flush.assert_called_once()
        self.mock_db.refresh.assert_called_once_with(mock_obj)
        assert result == mock_obj

    @pytest.mark.asyncio
    async def test_update_ignores_non_existent_fields(self):
        """존재하지 않는 필드는 무시"""
        mock_obj = MagicMock(spec=["field1"])
        mock_obj.field1 = "old_value"
        self.mock_db.flush = AsyncMock()
        self.mock_db.refresh = AsyncMock()

        update_data = {"field1": "new_value", "non_existent": "value"}
        await self.crud.update(self.mock_db, mock_obj, update_data)

        self.mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_success(self):
        """레코드 삭제 성공"""
        mock_obj = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_obj
        self.mock_db.execute = AsyncMock(return_value=mock_result)
        self.mock_db.delete = AsyncMock()
        self.mock_db.flush = AsyncMock()

        with patch("backend.database.repositories.base.select") as mock_select:
            mock_select.return_value.where.return_value = MagicMock()
            result = await self.crud.delete(self.mock_db, "test-id")

        assert result is True
        self.mock_db.delete.assert_called_once_with(mock_obj)
        self.mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_returns_false_when_not_found(self):
        """삭제할 레코드가 없으면 False 반환"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        self.mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("backend.database.repositories.base.select") as mock_select:
            mock_select.return_value.where.return_value = MagicMock()
            result = await self.crud.delete(self.mock_db, "non-existent-id")

        assert result is False
        self.mock_db.delete.assert_not_called()


# =============================================================================
# SignalRepository 테스트
# =============================================================================
class TestSignalRepository:
    """SignalRepository 단위 테스트"""

    def setup_method(self):
        """테스트 설정"""
        self.mock_db = AsyncMock()
        self.repo = SignalRepository(Signal)
        self.mock_signal = MagicMock(spec=Signal)
        self.mock_signal.signal_id = "SIG-2025-001"
        self.mock_signal.title = "테스트 신호"
        self.mock_signal.status = SignalStatus.NEW
        self.mock_signal.source = SignalSource.KT
        self.mock_signal.channel = SignalChannel.DESK_RESEARCH

    @pytest.mark.asyncio
    async def test_get_by_id_success(self):
        """signal_id로 Signal 조회 성공"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = self.mock_signal
        self.mock_db.execute = AsyncMock(return_value=mock_result)

        result = await self.repo.get_by_id(self.mock_db, "SIG-2025-001")

        assert result == self.mock_signal
        assert result.signal_id == "SIG-2025-001"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self):
        """signal_id로 조회 시 없으면 None 반환"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        self.mock_db.execute = AsyncMock(return_value=mock_result)

        result = await self.repo.get_by_id(self.mock_db, "NON-EXISTENT")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_multi_filtered_no_filter(self):
        """필터 없이 Signal 목록 조회"""
        mock_signals = [self.mock_signal, MagicMock(spec=Signal)]
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_signals
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 2

        self.mock_db.execute = AsyncMock(side_effect=[mock_result, mock_count_result])

        items, total = await self.repo.get_multi_filtered(self.mock_db)

        assert len(items) == 2
        assert total == 2

    @pytest.mark.asyncio
    async def test_get_multi_filtered_with_source_filter(self):
        """source 필터로 Signal 목록 조회"""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [self.mock_signal]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1

        self.mock_db.execute = AsyncMock(side_effect=[mock_result, mock_count_result])

        items, total = await self.repo.get_multi_filtered(self.mock_db, source="KT")

        assert len(items) == 1
        assert total == 1

    @pytest.mark.asyncio
    async def test_get_multi_filtered_with_channel_filter(self):
        """channel 필터로 Signal 목록 조회"""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [self.mock_signal]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1

        self.mock_db.execute = AsyncMock(side_effect=[mock_result, mock_count_result])

        items, total = await self.repo.get_multi_filtered(self.mock_db, channel="데스크리서치")

        assert len(items) == 1
        assert total == 1

    @pytest.mark.asyncio
    async def test_get_multi_filtered_with_status_filter(self):
        """status 필터로 Signal 목록 조회"""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [self.mock_signal]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1

        self.mock_db.execute = AsyncMock(side_effect=[mock_result, mock_count_result])

        items, total = await self.repo.get_multi_filtered(self.mock_db, status="NEW")

        assert len(items) == 1
        assert total == 1

    @pytest.mark.asyncio
    async def test_get_multi_filtered_with_pagination(self):
        """페이지네이션 적용된 Signal 목록 조회"""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 100

        self.mock_db.execute = AsyncMock(side_effect=[mock_result, mock_count_result])

        items, total = await self.repo.get_multi_filtered(self.mock_db, skip=20, limit=10)

        assert len(items) == 0
        assert total == 100

    @pytest.mark.asyncio
    async def test_get_stats_success(self):
        """Signal 통계 조회 성공"""
        # total
        mock_total_result = MagicMock()
        mock_total_result.scalar.return_value = 10

        # 상태별 개수 (SignalStatus 7개)
        mock_status_results = [MagicMock() for _ in SignalStatus]
        for i, mock in enumerate(mock_status_results):
            mock.scalar.return_value = i + 1

        # 원천별 개수 (SignalSource 3개)
        mock_source_results = [MagicMock() for _ in SignalSource]
        for i, mock in enumerate(mock_source_results):
            mock.scalar.return_value = (i + 1) * 2

        self.mock_db.execute = AsyncMock(
            side_effect=[mock_total_result] + mock_status_results + mock_source_results
        )

        stats = await self.repo.get_stats(self.mock_db)

        assert stats["total"] == 10
        assert "by_status" in stats
        assert "by_source" in stats

    @pytest.mark.asyncio
    async def test_generate_signal_id_first_of_year(self):
        """올해 첫 Signal ID 생성"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        self.mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("backend.database.repositories.signal.datetime") as mock_datetime:
            mock_datetime.now.return_value.year = 2025

            signal_id = await self.repo.generate_signal_id(self.mock_db)

        assert signal_id == "SIG-2025-001"

    @pytest.mark.asyncio
    async def test_generate_signal_id_increment(self):
        """기존 Signal이 있을 때 ID 증가"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "SIG-2025-005"
        self.mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("backend.database.repositories.signal.datetime") as mock_datetime:
            mock_datetime.now.return_value.year = 2025

            signal_id = await self.repo.generate_signal_id(self.mock_db)

        assert signal_id == "SIG-2025-006"

    def test_singleton_instance(self):
        """싱글톤 인스턴스 확인"""
        assert isinstance(signal_repo, SignalRepository)
        assert signal_repo.model == Signal


# =============================================================================
# ScorecardRepository 테스트
# =============================================================================
class TestScorecardRepository:
    """ScorecardRepository 단위 테스트"""

    def setup_method(self):
        """테스트 설정"""
        self.mock_db = AsyncMock()
        self.repo = ScorecardRepository(Scorecard)
        self.mock_scorecard = MagicMock(spec=Scorecard)
        self.mock_scorecard.scorecard_id = "SCR-2025-001"
        self.mock_scorecard.signal_id = "SIG-2025-001"
        self.mock_scorecard.total_score = 85.0
        self.mock_scorecard.recommendation = {"decision": "GO"}

    @pytest.mark.asyncio
    async def test_get_by_id_success(self):
        """scorecard_id로 Scorecard 조회 성공"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = self.mock_scorecard
        self.mock_db.execute = AsyncMock(return_value=mock_result)

        result = await self.repo.get_by_id(self.mock_db, "SCR-2025-001")

        assert result == self.mock_scorecard
        assert result.scorecard_id == "SCR-2025-001"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self):
        """scorecard_id로 조회 시 없으면 None 반환"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        self.mock_db.execute = AsyncMock(return_value=mock_result)

        result = await self.repo.get_by_id(self.mock_db, "NON-EXISTENT")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_signal_id_success(self):
        """signal_id로 Scorecard 조회 성공"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = self.mock_scorecard
        self.mock_db.execute = AsyncMock(return_value=mock_result)

        result = await self.repo.get_by_signal_id(self.mock_db, "SIG-2025-001")

        assert result == self.mock_scorecard
        assert result.signal_id == "SIG-2025-001"

    @pytest.mark.asyncio
    async def test_get_by_signal_id_not_found(self):
        """signal_id로 조회 시 없으면 None 반환"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        self.mock_db.execute = AsyncMock(return_value=mock_result)

        result = await self.repo.get_by_signal_id(self.mock_db, "NON-EXISTENT")

        assert result is None

    @pytest.mark.asyncio
    async def test_generate_scorecard_id_first_of_year(self):
        """올해 첫 Scorecard ID 생성"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        self.mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("backend.database.repositories.scorecard.datetime") as mock_datetime:
            mock_datetime.now.return_value.year = 2025

            scorecard_id = await self.repo.generate_scorecard_id(self.mock_db)

        assert scorecard_id == "SCR-2025-001"

    @pytest.mark.asyncio
    async def test_generate_scorecard_id_increment(self):
        """기존 Scorecard가 있을 때 ID 증가"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "SCR-2025-010"
        self.mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("backend.database.repositories.scorecard.datetime") as mock_datetime:
            mock_datetime.now.return_value.year = 2025

            scorecard_id = await self.repo.generate_scorecard_id(self.mock_db)

        assert scorecard_id == "SCR-2025-011"

    @pytest.mark.asyncio
    async def test_get_multi_filtered_no_filter(self):
        """필터 없이 Scorecard 목록 조회"""
        mock_scorecards = [self.mock_scorecard, MagicMock(spec=Scorecard)]
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_scorecards
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 2

        self.mock_db.execute = AsyncMock(side_effect=[mock_result, mock_count_result])

        items, total = await self.repo.get_multi_filtered(self.mock_db)

        assert len(items) == 2
        assert total == 2

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="JSONB 쿼리는 실제 PostgreSQL DB 필요 - 통합 테스트로 이동 필요")
    async def test_get_multi_filtered_with_decision_filter(self):
        """decision 필터로 Scorecard 목록 조회"""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [self.mock_scorecard]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1

        self.mock_db.execute = AsyncMock(side_effect=[mock_result, mock_count_result])

        items, total = await self.repo.get_multi_filtered(self.mock_db, decision="GO")

        assert len(items) == 1
        assert total == 1

    @pytest.mark.asyncio
    async def test_get_multi_filtered_with_min_score(self):
        """min_score 필터로 Scorecard 목록 조회"""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [self.mock_scorecard]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1

        self.mock_db.execute = AsyncMock(side_effect=[mock_result, mock_count_result])

        items, total = await self.repo.get_multi_filtered(self.mock_db, min_score=80.0)

        assert len(items) == 1
        assert total == 1

    @pytest.mark.asyncio
    async def test_get_multi_filtered_with_max_score(self):
        """max_score 필터로 Scorecard 목록 조회"""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [self.mock_scorecard]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1

        self.mock_db.execute = AsyncMock(side_effect=[mock_result, mock_count_result])

        items, total = await self.repo.get_multi_filtered(self.mock_db, max_score=90.0)

        assert len(items) == 1
        assert total == 1

    @pytest.mark.asyncio
    async def test_get_stats_success(self):
        """Scorecard 통계 조회 성공"""
        mock_total_result = MagicMock()
        mock_total_result.scalar.return_value = 10

        mock_avg_result = MagicMock()
        mock_avg_result.scalar.return_value = 75.5

        self.mock_db.execute = AsyncMock(side_effect=[mock_total_result, mock_avg_result])

        stats = await self.repo.get_stats(self.mock_db)

        assert stats["total"] == 10
        assert stats["average_score"] == 75.5

    @pytest.mark.asyncio
    async def test_get_stats_empty_table(self):
        """빈 테이블일 때 통계"""
        mock_total_result = MagicMock()
        mock_total_result.scalar.return_value = 0

        mock_avg_result = MagicMock()
        mock_avg_result.scalar.return_value = None

        self.mock_db.execute = AsyncMock(side_effect=[mock_total_result, mock_avg_result])

        stats = await self.repo.get_stats(self.mock_db)

        assert stats["total"] == 0
        assert stats["average_score"] == 0

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="JSONB 쿼리는 실제 PostgreSQL DB 필요 - 통합 테스트로 이동 필요")
    async def test_get_distribution_stats_success(self):
        """Scorecard 분포 통계 조회 성공"""
        mock_results = []

        # total
        mock_total = MagicMock()
        mock_total.scalar.return_value = 10
        mock_results.append(mock_total)

        # GO, PIVOT, HOLD, NO_GO counts
        for count in [5, 2, 2, 1]:
            mock_count = MagicMock()
            mock_count.scalar.return_value = count
            mock_results.append(mock_count)

        # avg score
        mock_avg = MagicMock()
        mock_avg.scalar.return_value = 72.5
        mock_results.append(mock_avg)

        # red flag count
        mock_red_flag = MagicMock()
        mock_red_flag.scalar.return_value = 3
        mock_results.append(mock_red_flag)

        self.mock_db.execute = AsyncMock(side_effect=mock_results)

        stats = await self.repo.get_distribution_stats(self.mock_db)

        assert stats["total_scored"] == 10
        assert stats["go_count"] == 5
        assert stats["pivot_count"] == 2
        assert stats["hold_count"] == 2
        assert stats["no_go_count"] == 1
        assert stats["average_score"] == 72.5
        assert stats["red_flag_rate"] == 30.0

    @pytest.mark.asyncio
    async def test_get_distribution_stats_empty(self):
        """빈 테이블일 때 분포 통계"""
        mock_total = MagicMock()
        mock_total.scalar.return_value = 0
        self.mock_db.execute = AsyncMock(return_value=mock_total)

        stats = await self.repo.get_distribution_stats(self.mock_db)

        assert stats["total_scored"] == 0
        assert stats["go_count"] == 0
        assert stats["average_score"] == 0
        assert stats["red_flag_rate"] == 0

    def test_singleton_instance(self):
        """싱글톤 인스턴스 확인"""
        assert isinstance(scorecard_repo, ScorecardRepository)
        assert scorecard_repo.model == Scorecard


# =============================================================================
# BriefRepository 테스트
# =============================================================================
class TestBriefRepository:
    """BriefRepository 단위 테스트"""

    def setup_method(self):
        """테스트 설정"""
        self.mock_db = AsyncMock()
        self.repo = BriefRepository(OpportunityBrief)
        self.mock_brief = MagicMock(spec=OpportunityBrief)
        self.mock_brief.brief_id = "BRF-2025-001"
        self.mock_brief.signal_id = "SIG-2025-001"
        self.mock_brief.title = "테스트 Brief"
        self.mock_brief.status = BriefStatus.DRAFT
        self.mock_brief.owner = "홍길동"

    @pytest.mark.asyncio
    async def test_get_by_id_success(self):
        """brief_id로 Brief 조회 성공"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = self.mock_brief
        self.mock_db.execute = AsyncMock(return_value=mock_result)

        result = await self.repo.get_by_id(self.mock_db, "BRF-2025-001")

        assert result == self.mock_brief
        assert result.brief_id == "BRF-2025-001"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self):
        """brief_id로 조회 시 없으면 None 반환"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        self.mock_db.execute = AsyncMock(return_value=mock_result)

        result = await self.repo.get_by_id(self.mock_db, "NON-EXISTENT")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_signal_id_success(self):
        """signal_id로 Brief 조회 성공"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = self.mock_brief
        self.mock_db.execute = AsyncMock(return_value=mock_result)

        result = await self.repo.get_by_signal_id(self.mock_db, "SIG-2025-001")

        assert result == self.mock_brief
        assert result.signal_id == "SIG-2025-001"

    @pytest.mark.asyncio
    async def test_get_by_signal_id_not_found(self):
        """signal_id로 조회 시 없으면 None 반환"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        self.mock_db.execute = AsyncMock(return_value=mock_result)

        result = await self.repo.get_by_signal_id(self.mock_db, "NON-EXISTENT")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_multi_filtered_no_filter(self):
        """필터 없이 Brief 목록 조회"""
        mock_briefs = [self.mock_brief, MagicMock(spec=OpportunityBrief)]
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_briefs
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 2

        self.mock_db.execute = AsyncMock(side_effect=[mock_result, mock_count_result])

        items, total = await self.repo.get_multi_filtered(self.mock_db)

        assert len(items) == 2
        assert total == 2

    @pytest.mark.asyncio
    async def test_get_multi_filtered_with_status_filter(self):
        """status 필터로 Brief 목록 조회"""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [self.mock_brief]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1

        self.mock_db.execute = AsyncMock(side_effect=[mock_result, mock_count_result])

        items, total = await self.repo.get_multi_filtered(self.mock_db, status="DRAFT")

        assert len(items) == 1
        assert total == 1

    @pytest.mark.asyncio
    async def test_get_multi_filtered_with_owner_filter(self):
        """owner 필터로 Brief 목록 조회"""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [self.mock_brief]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1

        self.mock_db.execute = AsyncMock(side_effect=[mock_result, mock_count_result])

        items, total = await self.repo.get_multi_filtered(self.mock_db, owner="홍길동")

        assert len(items) == 1
        assert total == 1

    @pytest.mark.asyncio
    async def test_generate_brief_id_first_of_year(self):
        """올해 첫 Brief ID 생성"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        self.mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("backend.database.repositories.brief.datetime") as mock_datetime:
            mock_datetime.now.return_value.year = 2025

            brief_id = await self.repo.generate_brief_id(self.mock_db)

        assert brief_id == "BRF-2025-001"

    @pytest.mark.asyncio
    async def test_generate_brief_id_increment(self):
        """기존 Brief가 있을 때 ID 증가"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "BRF-2025-015"
        self.mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("backend.database.repositories.brief.datetime") as mock_datetime:
            mock_datetime.now.return_value.year = 2025

            brief_id = await self.repo.generate_brief_id(self.mock_db)

        assert brief_id == "BRF-2025-016"

    @pytest.mark.asyncio
    async def test_get_stats_success(self):
        """Brief 통계 조회 성공"""
        mock_results = []

        # total
        mock_total = MagicMock()
        mock_total.scalar.return_value = 10
        mock_results.append(mock_total)

        # 상태별 개수 (BriefStatus 6개)
        for i in range(len(BriefStatus)):
            mock_count = MagicMock()
            mock_count.scalar.return_value = i + 1
            mock_results.append(mock_count)

        self.mock_db.execute = AsyncMock(side_effect=mock_results)

        stats = await self.repo.get_stats(self.mock_db)

        assert stats["total"] == 10
        assert "by_status" in stats

    @pytest.mark.asyncio
    async def test_get_stats_empty_table(self):
        """빈 테이블일 때 통계"""
        mock_results = []

        mock_total = MagicMock()
        mock_total.scalar.return_value = 0
        mock_results.append(mock_total)

        for _ in range(len(BriefStatus)):
            mock_count = MagicMock()
            mock_count.scalar.return_value = 0
            mock_results.append(mock_count)

        self.mock_db.execute = AsyncMock(side_effect=mock_results)

        stats = await self.repo.get_stats(self.mock_db)

        assert stats["total"] == 0

    @pytest.mark.asyncio
    async def test_update_status_success(self):
        """Brief 상태 업데이트 성공"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = self.mock_brief
        self.mock_db.execute = AsyncMock(return_value=mock_result)
        self.mock_db.flush = AsyncMock()

        result = await self.repo.update_status(self.mock_db, "BRF-2025-001", BriefStatus.APPROVED)

        assert result == self.mock_brief
        assert self.mock_brief.status == BriefStatus.APPROVED

    @pytest.mark.asyncio
    async def test_update_status_with_confluence_url(self):
        """Brief 상태 업데이트 + Confluence URL 설정"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = self.mock_brief
        self.mock_db.execute = AsyncMock(return_value=mock_result)
        self.mock_db.flush = AsyncMock()

        result = await self.repo.update_status(
            self.mock_db,
            "BRF-2025-001",
            BriefStatus.APPROVED,
            confluence_url="https://confluence.example.com/page/123",
        )

        assert result == self.mock_brief
        assert self.mock_brief.confluence_url == "https://confluence.example.com/page/123"

    @pytest.mark.asyncio
    async def test_update_status_not_found(self):
        """존재하지 않는 Brief 상태 업데이트"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        self.mock_db.execute = AsyncMock(return_value=mock_result)

        result = await self.repo.update_status(self.mock_db, "NON-EXISTENT", BriefStatus.APPROVED)

        assert result is None

    def test_singleton_instance(self):
        """싱글톤 인스턴스 확인"""
        assert isinstance(brief_repo, BriefRepository)
        assert brief_repo.model == OpportunityBrief


# =============================================================================
# PlayRecordRepository 테스트
# =============================================================================
class TestPlayRecordRepository:
    """PlayRecordRepository 단위 테스트"""

    def setup_method(self):
        """테스트 설정"""
        self.mock_db = AsyncMock()
        self.repo = PlayRecordRepository(PlayRecord)
        self.mock_play = MagicMock(spec=PlayRecord)
        self.mock_play.play_id = "PLAY-001"
        self.mock_play.play_name = "AI 데이터 분석 Play"
        self.mock_play.status = "G"
        self.mock_play.owner = "김철수"
        self.mock_play.activity_qtd = 5
        self.mock_play.signal_qtd = 3
        self.mock_play.brief_qtd = 1
        self.mock_play.s2_qtd = 0
        self.mock_play.s3_qtd = 0
        self.mock_play.due_date = None
        self.mock_play.last_activity_date = date.today()
        self.mock_play.next_action = "고객 미팅 예정"

    @pytest.mark.asyncio
    async def test_get_by_id_success(self):
        """play_id로 PlayRecord 조회 성공"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = self.mock_play
        self.mock_db.execute = AsyncMock(return_value=mock_result)

        result = await self.repo.get_by_id(self.mock_db, "PLAY-001")

        assert result == self.mock_play
        assert result.play_id == "PLAY-001"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self):
        """play_id로 조회 시 없으면 None 반환"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        self.mock_db.execute = AsyncMock(return_value=mock_result)

        result = await self.repo.get_by_id(self.mock_db, "NON-EXISTENT")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_all_success(self):
        """모든 PlayRecord 조회"""
        mock_plays = [self.mock_play, MagicMock(spec=PlayRecord)]
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_plays
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        self.mock_db.execute = AsyncMock(return_value=mock_result)

        result = await self.repo.get_all(self.mock_db)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_increment_activity_success(self):
        """Play activity_qtd 증가 성공"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = self.mock_play
        self.mock_db.execute = AsyncMock(return_value=mock_result)
        self.mock_db.flush = AsyncMock()
        self.mock_db.refresh = AsyncMock()

        initial_count = self.mock_play.activity_qtd
        result = await self.repo.increment_activity(self.mock_db, "PLAY-001")

        assert result == self.mock_play
        assert self.mock_play.activity_qtd == initial_count + 1

    @pytest.mark.asyncio
    async def test_increment_activity_not_found(self):
        """존재하지 않는 Play activity 증가"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        self.mock_db.execute = AsyncMock(return_value=mock_result)

        result = await self.repo.increment_activity(self.mock_db, "NON-EXISTENT")

        assert result is None

    @pytest.mark.asyncio
    async def test_increment_signal_success(self):
        """Play signal_qtd 증가 성공"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = self.mock_play
        self.mock_db.execute = AsyncMock(return_value=mock_result)
        self.mock_db.flush = AsyncMock()
        self.mock_db.refresh = AsyncMock()

        initial_count = self.mock_play.signal_qtd
        result = await self.repo.increment_signal(self.mock_db, "PLAY-001")

        assert result == self.mock_play
        assert self.mock_play.signal_qtd == initial_count + 1

    @pytest.mark.asyncio
    async def test_increment_signal_not_found(self):
        """존재하지 않는 Play signal 증가"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        self.mock_db.execute = AsyncMock(return_value=mock_result)

        result = await self.repo.increment_signal(self.mock_db, "NON-EXISTENT")

        assert result is None

    @pytest.mark.asyncio
    async def test_increment_brief_success(self):
        """Play brief_qtd 증가 성공"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = self.mock_play
        self.mock_db.execute = AsyncMock(return_value=mock_result)
        self.mock_db.flush = AsyncMock()
        self.mock_db.refresh = AsyncMock()

        initial_count = self.mock_play.brief_qtd
        result = await self.repo.increment_brief(self.mock_db, "PLAY-001")

        assert result == self.mock_play
        assert self.mock_play.brief_qtd == initial_count + 1

    @pytest.mark.asyncio
    async def test_increment_brief_not_found(self):
        """존재하지 않는 Play brief 증가"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        self.mock_db.execute = AsyncMock(return_value=mock_result)

        result = await self.repo.increment_brief(self.mock_db, "NON-EXISTENT")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_multi_filtered_no_filter(self):
        """필터 없이 PlayRecord 목록 조회"""
        mock_plays = [self.mock_play, MagicMock(spec=PlayRecord)]
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_plays
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 2

        self.mock_db.execute = AsyncMock(side_effect=[mock_result, mock_count_result])

        items, total = await self.repo.get_multi_filtered(self.mock_db)

        assert len(items) == 2
        assert total == 2

    @pytest.mark.asyncio
    async def test_get_multi_filtered_with_status_filter(self):
        """status 필터로 PlayRecord 목록 조회"""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [self.mock_play]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1

        self.mock_db.execute = AsyncMock(side_effect=[mock_result, mock_count_result])

        items, total = await self.repo.get_multi_filtered(self.mock_db, status="G")

        assert len(items) == 1
        assert total == 1

    @pytest.mark.asyncio
    async def test_get_multi_filtered_with_owner_filter(self):
        """owner 필터로 PlayRecord 목록 조회"""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [self.mock_play]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1

        self.mock_db.execute = AsyncMock(side_effect=[mock_result, mock_count_result])

        items, total = await self.repo.get_multi_filtered(self.mock_db, owner="김철수")

        assert len(items) == 1
        assert total == 1

    @pytest.mark.asyncio
    async def test_get_stats_success(self):
        """Play 통계 조회 성공"""
        mock_results = []

        # total plays
        mock_total = MagicMock()
        mock_total.scalar.return_value = 5
        mock_results.append(mock_total)

        # sum results (activity, signal, brief, s2, s3)
        for value in [25, 15, 8, 3, 1]:
            mock_sum = MagicMock()
            mock_sum.scalar.return_value = value
            mock_results.append(mock_sum)

        self.mock_db.execute = AsyncMock(side_effect=mock_results)

        stats = await self.repo.get_stats(self.mock_db)

        assert stats["total_plays"] == 5
        assert stats["total_activity"] == 25
        assert stats["total_signal"] == 15
        assert stats["total_brief"] == 8
        assert stats["total_s2"] == 3
        assert stats["total_s3"] == 1

    @pytest.mark.asyncio
    async def test_get_stats_empty_table(self):
        """빈 테이블일 때 통계"""
        mock_results = []

        for _ in range(6):  # total + 5 sums
            mock_result = MagicMock()
            mock_result.scalar.return_value = 0
            mock_results.append(mock_result)

        self.mock_db.execute = AsyncMock(side_effect=mock_results)

        stats = await self.repo.get_stats(self.mock_db)

        assert stats["total_plays"] == 0
        assert stats["total_activity"] == 0

    @pytest.mark.asyncio
    async def test_get_kpi_digest_success(self):
        """KPI 요약 리포트 조회 성공"""
        mock_results = []

        # get_stats 호출 결과 (6개)
        for value in [5, 25, 15, 8, 3, 1]:
            mock_result = MagicMock()
            mock_result.scalar.return_value = value
            mock_results.append(mock_result)

        # status별 개수 (G, Y, R)
        for count in [3, 1, 1]:
            mock_status = MagicMock()
            mock_status.scalar.return_value = count
            mock_results.append(mock_status)

        self.mock_db.execute = AsyncMock(side_effect=mock_results)

        digest = await self.repo.get_kpi_digest(self.mock_db, period="week")

        assert digest["period"] == "week"
        assert digest["activity_actual"] == 25
        assert digest["signal_actual"] == 15
        assert digest["brief_actual"] == 8
        assert digest["s2_actual"] == 3
        assert "status_summary" in digest
        assert digest["status_summary"]["green"] == 3
        assert digest["status_summary"]["yellow"] == 1
        assert digest["status_summary"]["red"] == 1

    @pytest.mark.asyncio
    async def test_get_alerts_success(self):
        """지연/경고 Play 조회 성공"""
        # Yellow plays
        mock_yellow_plays = [MagicMock(play_id="PLAY-Y1"), MagicMock(play_id="PLAY-Y2")]
        mock_yellow_scalars = MagicMock()
        mock_yellow_scalars.all.return_value = mock_yellow_plays
        mock_yellow_result = MagicMock()
        mock_yellow_result.scalars.return_value = mock_yellow_scalars

        # Red plays
        mock_red_plays = [MagicMock(play_id="PLAY-R1")]
        mock_red_scalars = MagicMock()
        mock_red_scalars.all.return_value = mock_red_plays
        mock_red_result = MagicMock()
        mock_red_result.scalars.return_value = mock_red_scalars

        # Overdue plays
        mock_overdue_play = MagicMock(
            play_id="PLAY-OD1",
            due_date=date.today() - timedelta(days=1),
            next_action="지연된 작업",
        )
        mock_overdue_scalars = MagicMock()
        mock_overdue_scalars.all.return_value = [mock_overdue_play]
        mock_overdue_result = MagicMock()
        mock_overdue_result.scalars.return_value = mock_overdue_scalars

        # Stale plays
        mock_stale_plays = [MagicMock(play_id="PLAY-S1")]
        mock_stale_scalars = MagicMock()
        mock_stale_scalars.all.return_value = mock_stale_plays
        mock_stale_result = MagicMock()
        mock_stale_result.scalars.return_value = mock_stale_scalars

        self.mock_db.execute = AsyncMock(
            side_effect=[
                mock_yellow_result,
                mock_red_result,
                mock_overdue_result,
                mock_stale_result,
            ]
        )

        alerts = await self.repo.get_alerts(self.mock_db)

        assert len(alerts["yellow_plays"]) == 2
        assert len(alerts["red_plays"]) == 1
        assert len(alerts["overdue_plays"]) == 1
        assert len(alerts["stale_plays"]) == 1

    @pytest.mark.asyncio
    async def test_get_alerts_no_issues(self):
        """경고 없을 때"""
        for _ in range(4):
            mock_scalars = MagicMock()
            mock_scalars.all.return_value = []
            mock_result = MagicMock()
            mock_result.scalars.return_value = mock_scalars

        mock_empty_result = MagicMock()
        mock_empty_scalars = MagicMock()
        mock_empty_scalars.all.return_value = []
        mock_empty_result.scalars.return_value = mock_empty_scalars

        self.mock_db.execute = AsyncMock(return_value=mock_empty_result)

        alerts = await self.repo.get_alerts(self.mock_db)

        assert len(alerts["yellow_plays"]) == 0
        assert len(alerts["red_plays"]) == 0
        assert len(alerts["overdue_plays"]) == 0
        assert len(alerts["stale_plays"]) == 0

    @pytest.mark.asyncio
    async def test_update_status_success(self):
        """Play 상태 업데이트 성공"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = self.mock_play
        self.mock_db.execute = AsyncMock(return_value=mock_result)
        self.mock_db.flush = AsyncMock()

        result = await self.repo.update_status(self.mock_db, "PLAY-001", "Y")

        assert result == self.mock_play
        assert self.mock_play.status == "Y"

    @pytest.mark.asyncio
    async def test_update_status_with_next_action(self):
        """Play 상태 업데이트 + next_action 설정"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = self.mock_play
        self.mock_db.execute = AsyncMock(return_value=mock_result)
        self.mock_db.flush = AsyncMock()

        result = await self.repo.update_status(
            self.mock_db, "PLAY-001", "Y", next_action="고객 연락 필요"
        )

        assert result == self.mock_play
        assert self.mock_play.next_action == "고객 연락 필요"

    @pytest.mark.asyncio
    async def test_update_status_with_due_date(self):
        """Play 상태 업데이트 + due_date 설정"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = self.mock_play
        self.mock_db.execute = AsyncMock(return_value=mock_result)
        self.mock_db.flush = AsyncMock()

        new_due_date = date.today() + timedelta(days=7)
        result = await self.repo.update_status(self.mock_db, "PLAY-001", "Y", due_date=new_due_date)

        assert result == self.mock_play
        assert self.mock_play.due_date == new_due_date

    @pytest.mark.asyncio
    async def test_update_status_not_found(self):
        """존재하지 않는 Play 상태 업데이트"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        self.mock_db.execute = AsyncMock(return_value=mock_result)

        result = await self.repo.update_status(self.mock_db, "NON-EXISTENT", "R")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_timeline_returns_empty(self):
        """타임라인 조회 (현재 빈 리스트 반환)"""
        result = await self.repo.get_timeline(self.mock_db, "PLAY-001")

        assert result == []

    @pytest.mark.asyncio
    async def test_get_leaderboard_success(self):
        """Play 성과 순위 조회 성공"""
        mock_plays = [
            MagicMock(play_id="PLAY-001", play_name="Play 1", signal_qtd=10, brief_qtd=5),
            MagicMock(play_id="PLAY-002", play_name="Play 2", signal_qtd=8, brief_qtd=3),
        ]
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_plays
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        self.mock_db.execute = AsyncMock(return_value=mock_result)

        leaderboard = await self.repo.get_leaderboard(self.mock_db, period="week")

        assert leaderboard["period"] == "week"
        assert len(leaderboard["top_plays"]) == 2
        assert leaderboard["top_plays"][0]["play_id"] == "PLAY-001"
        assert leaderboard["top_plays"][0]["signal_qtd"] == 10

    @pytest.mark.asyncio
    async def test_get_leaderboard_empty(self):
        """Play 없을 때 성과 순위"""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        self.mock_db.execute = AsyncMock(return_value=mock_result)

        leaderboard = await self.repo.get_leaderboard(self.mock_db)

        assert len(leaderboard["top_plays"]) == 0

    def test_singleton_instance(self):
        """싱글톤 인스턴스 확인"""
        assert isinstance(play_record_repo, PlayRecordRepository)
        assert play_record_repo.model == PlayRecord


# =============================================================================
# 공통 테스트 - 에지 케이스
# =============================================================================
class TestRepositoryEdgeCases:
    """Repository 에지 케이스 테스트"""

    def setup_method(self):
        """테스트 설정"""
        self.mock_db = AsyncMock()

    @pytest.mark.asyncio
    async def test_crud_base_with_none_model(self):
        """CRUDBase 모델이 None일 때"""
        crud = CRUDBase(None)
        assert crud.model is None

    @pytest.mark.asyncio
    async def test_signal_repo_generate_id_with_large_number(self):
        """큰 번호의 Signal ID 증가"""
        repo = SignalRepository(Signal)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "SIG-2025-999"
        self.mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("backend.database.repositories.signal.datetime") as mock_datetime:
            mock_datetime.now.return_value.year = 2025

            signal_id = await repo.generate_signal_id(self.mock_db)

        assert signal_id == "SIG-2025-1000"

    @pytest.mark.asyncio
    async def test_brief_repo_update_status_no_confluence_url(self):
        """Brief 상태 업데이트 시 confluence_url 없음"""
        repo = BriefRepository(OpportunityBrief)
        mock_brief = MagicMock(spec=OpportunityBrief)
        mock_brief.confluence_url = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_brief
        self.mock_db.execute = AsyncMock(return_value=mock_result)
        self.mock_db.flush = AsyncMock()

        await repo.update_status(self.mock_db, "BRF-001", BriefStatus.REVIEW)

        assert mock_brief.confluence_url is None

    @pytest.mark.asyncio
    async def test_play_record_repo_stats_with_none_values(self):
        """PlayRecord 통계 조회 시 None 값 처리"""
        repo = PlayRecordRepository(PlayRecord)
        mock_results = []

        # total
        mock_total = MagicMock()
        mock_total.scalar.return_value = 1
        mock_results.append(mock_total)

        # sum results with None
        for _ in range(5):
            mock_sum = MagicMock()
            mock_sum.scalar.return_value = None
            mock_results.append(mock_sum)

        self.mock_db.execute = AsyncMock(side_effect=mock_results)

        stats = await repo.get_stats(self.mock_db)

        assert stats["total_plays"] == 1
        assert stats["total_activity"] == 0
        assert stats["total_signal"] == 0

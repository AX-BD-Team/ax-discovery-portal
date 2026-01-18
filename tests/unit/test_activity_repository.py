"""
ActivityRepository 단위 테스트

Activity CRUD 작업 및 중복 체크 테스트
"""

from datetime import datetime

import pytest

from backend.database.models.entity import EntityType
from backend.database.repositories.activity import activity_repo


class TestActivityRepository:
    """ActivityRepository 테스트"""

    @pytest.mark.asyncio
    async def test_create_activity_basic(self, test_db_session):
        """기본 Activity 생성 테스트"""
        activity_data = {
            "title": "AI 컨퍼런스 2026",
            "url": "https://example.com/ai-conf-2026",
            "date": "2026-03-15",
            "organizer": "Tech Company",
            "description": "AI 기술 트렌드 발표",
            "play_id": "EXT_Desk_D01_Seminar",
            "source_type": "rss",
            "categories": ["AI", "기술"],
        }

        entity = await activity_repo.create_activity(test_db_session, activity_data)

        assert entity is not None
        assert entity.entity_id.startswith("ACT-")
        assert entity.entity_type == EntityType.ACTIVITY
        assert entity.name == "AI 컨퍼런스 2026"
        assert entity.properties["url"] == "https://example.com/ai-conf-2026"
        assert entity.properties["source_type"] == "rss"

    @pytest.mark.asyncio
    async def test_create_activity_with_custom_id(self, test_db_session):
        """사용자 지정 ID로 Activity 생성"""
        activity_data = {
            "activity_id": "ACT-CUSTOM-001",
            "title": "커스텀 세미나",
            "url": "https://example.com/custom",
        }

        entity = await activity_repo.create_activity(test_db_session, activity_data)

        assert entity.entity_id == "ACT-CUSTOM-001"

    @pytest.mark.asyncio
    async def test_get_by_id(self, test_db_session):
        """ID로 Activity 조회"""
        # 생성
        activity_data = {
            "title": "조회 테스트 세미나",
            "url": "https://example.com/test-get",
        }
        created = await activity_repo.create_activity(test_db_session, activity_data)
        await test_db_session.commit()

        # 조회
        found = await activity_repo.get_by_id(test_db_session, created.entity_id)

        assert found is not None
        assert found.entity_id == created.entity_id
        assert found.name == "조회 테스트 세미나"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, test_db_session):
        """존재하지 않는 ID 조회"""
        found = await activity_repo.get_by_id(test_db_session, "ACT-NONEXISTENT")

        assert found is None

    @pytest.mark.asyncio
    async def test_get_by_url(self, test_db_session):
        """URL로 Activity 조회"""
        url = "https://example.com/unique-url-test"
        activity_data = {
            "title": "URL 테스트 세미나",
            "url": url,
        }
        await activity_repo.create_activity(test_db_session, activity_data)
        await test_db_session.commit()

        found = await activity_repo.get_by_url(test_db_session, url)

        assert found is not None
        assert found.properties["url"] == url

    @pytest.mark.asyncio
    async def test_get_by_external_id(self, test_db_session):
        """외부 ID로 Activity 조회"""
        external_id = "festa_12345"
        activity_data = {
            "title": "Festa 이벤트",
            "url": "https://festa.io/events/12345",
            "external_id": external_id,
            "source_type": "festa",
        }
        await activity_repo.create_activity(test_db_session, activity_data)
        await test_db_session.commit()

        found = await activity_repo.get_by_external_id(test_db_session, external_id)

        assert found is not None
        assert found.external_ref_id == external_id

    @pytest.mark.asyncio
    async def test_check_duplicate_by_url(self, test_db_session):
        """URL 중복 체크"""
        url = "https://example.com/duplicate-test"
        activity_data = {
            "title": "중복 테스트",
            "url": url,
        }
        await activity_repo.create_activity(test_db_session, activity_data)
        await test_db_session.commit()

        # 동일 URL로 중복 체크
        duplicate = await activity_repo.check_duplicate(
            test_db_session,
            url=url,
        )

        assert duplicate is not None

    @pytest.mark.asyncio
    async def test_check_duplicate_by_external_id(self, test_db_session):
        """외부 ID 중복 체크"""
        external_id = "eventbrite_99999"
        activity_data = {
            "title": "Eventbrite 이벤트",
            "url": "https://eventbrite.com/e/99999",
            "external_id": external_id,
        }
        await activity_repo.create_activity(test_db_session, activity_data)
        await test_db_session.commit()

        duplicate = await activity_repo.check_duplicate(
            test_db_session,
            external_id=external_id,
        )

        assert duplicate is not None

    @pytest.mark.asyncio
    async def test_check_duplicate_by_title_and_date(self, test_db_session):
        """제목+날짜 중복 체크"""
        activity_data = {
            "title": "연례 AI 서밋",
            "url": "https://example.com/ai-summit-1",
            "date": "2026-06-01",
        }
        await activity_repo.create_activity(test_db_session, activity_data)
        await test_db_session.commit()

        # 동일 제목+날짜로 중복 체크
        duplicate = await activity_repo.check_duplicate(
            test_db_session,
            title="연례 AI 서밋",
            date="2026-06-01",
        )

        assert duplicate is not None

    @pytest.mark.asyncio
    async def test_check_duplicate_not_found(self, test_db_session):
        """중복 없음 확인"""
        duplicate = await activity_repo.check_duplicate(
            test_db_session,
            url="https://example.com/new-unique-url",
            title="완전히 새로운 세미나",
            date="2099-12-31",
        )

        assert duplicate is None

    @pytest.mark.asyncio
    async def test_list_by_play(self, test_db_session):
        """Play별 Activity 목록 조회"""
        play_id = "TEST_Play_001"

        # 3개 생성
        for i in range(3):
            await activity_repo.create_activity(
                test_db_session,
                {
                    "title": f"Play 테스트 세미나 {i}",
                    "url": f"https://example.com/play-test-{i}",
                    "play_id": play_id,
                },
            )
        await test_db_session.commit()

        items, total = await activity_repo.list_by_play(test_db_session, play_id)

        assert total == 3
        assert len(items) == 3

    @pytest.mark.asyncio
    async def test_list_by_source_type(self, test_db_session):
        """소스 타입별 Activity 목록 조회"""
        # RSS 2개, Festa 1개 생성
        for i in range(2):
            await activity_repo.create_activity(
                test_db_session,
                {
                    "title": f"RSS 세미나 {i}",
                    "url": f"https://example.com/rss-{i}",
                    "source_type": "rss",
                },
            )
        await activity_repo.create_activity(
            test_db_session,
            {
                "title": "Festa 이벤트",
                "url": "https://festa.io/events/test",
                "source_type": "festa",
            },
        )
        await test_db_session.commit()

        # RSS만 조회
        rss_items, rss_total = await activity_repo.list_by_source_type(test_db_session, "rss")

        assert rss_total == 2

    @pytest.mark.asyncio
    async def test_generate_activity_id(self, test_db_session):
        """Activity ID 자동 생성"""
        id1 = await activity_repo.generate_activity_id(test_db_session)

        # 첫 번째 ID 형식 확인
        current_year = datetime.now().year
        assert id1.startswith(f"ACT-{current_year}-")
        assert id1.endswith("00001")

        # Activity 생성 후 다음 ID 확인
        await activity_repo.create_activity(
            test_db_session,
            {
                "activity_id": id1,
                "title": "ID 테스트",
                "url": "https://example.com/id-test",
            },
        )
        await test_db_session.commit()

        id2 = await activity_repo.generate_activity_id(test_db_session)
        assert id2.endswith("00002")

    @pytest.mark.asyncio
    async def test_get_stats(self, test_db_session):
        """Activity 통계 조회"""
        # 다양한 소스의 Activity 생성
        await activity_repo.create_activity(
            test_db_session,
            {
                "title": "RSS 1",
                "url": "https://example.com/stats-rss-1",
                "source_type": "rss",
            },
        )
        await activity_repo.create_activity(
            test_db_session,
            {
                "title": "Festa 1",
                "url": "https://example.com/stats-festa-1",
                "source_type": "festa",
            },
        )
        await test_db_session.commit()

        stats = await activity_repo.get_stats(test_db_session)

        assert stats["total"] >= 2
        assert "by_source_type" in stats
        assert "today_count" in stats


class TestActivityRepositoryEdgeCases:
    """ActivityRepository 엣지 케이스 테스트"""

    @pytest.mark.asyncio
    async def test_create_activity_minimal_data(self, test_db_session):
        """최소 데이터로 Activity 생성"""
        activity_data = {
            "title": "최소 데이터 세미나",
            "url": "https://example.com/minimal",
        }

        entity = await activity_repo.create_activity(test_db_session, activity_data)

        assert entity is not None
        assert entity.properties["source_type"] == "manual"  # 기본값
        assert entity.properties["play_id"] == "EXT_Desk_D01_Seminar"  # 기본값

    @pytest.mark.asyncio
    async def test_create_activity_with_date_parsing(self, test_db_session):
        """날짜 파싱이 포함된 Activity 생성"""
        activity_data = {
            "title": "날짜 테스트",
            "url": "https://example.com/date-test",
            "date": "2026-12-25",
        }

        entity = await activity_repo.create_activity(test_db_session, activity_data)

        assert entity.published_at is not None
        assert entity.published_at.year == 2026
        assert entity.published_at.month == 12
        assert entity.published_at.day == 25

    @pytest.mark.asyncio
    async def test_list_with_pagination(self, test_db_session):
        """페이지네이션 테스트"""
        play_id = "PAGINATION_TEST"

        # 10개 생성
        for i in range(10):
            await activity_repo.create_activity(
                test_db_session,
                {
                    "title": f"페이지네이션 테스트 {i}",
                    "url": f"https://example.com/pagination-{i}",
                    "play_id": play_id,
                },
            )
        await test_db_session.commit()

        # 첫 페이지 (5개)
        items_page1, total = await activity_repo.list_by_play(
            test_db_session, play_id, limit=5, skip=0
        )
        assert len(items_page1) == 5
        assert total == 10

        # 두 번째 페이지 (5개)
        items_page2, _ = await activity_repo.list_by_play(test_db_session, play_id, limit=5, skip=5)
        assert len(items_page2) == 5

        # 페이지 내용이 다른지 확인
        page1_ids = {item.entity_id for item in items_page1}
        page2_ids = {item.entity_id for item in items_page2}
        assert page1_ids.isdisjoint(page2_ids)

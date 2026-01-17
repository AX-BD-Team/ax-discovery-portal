"""
세미나 수집기 인터페이스

모든 외부 소스 수집기의 기본 클래스 및 데이터 모델
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class SeminarInfo:
    """
    수집된 세미나 정보

    모든 소스에서 공통으로 사용하는 표준 데이터 구조
    """

    # 필수 필드
    title: str
    url: str
    source_type: str  # rss, festa, eventbrite

    # 선택 필드
    date: str | None = None  # YYYY-MM-DD 형식
    end_date: str | None = None  # 종료 날짜 (다일 행사)
    organizer: str | None = None
    description: str | None = None
    location: str | None = None  # 장소 (오프라인) 또는 "온라인"
    categories: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    # 외부 시스템 참조
    external_id: str | None = None  # RSS guid, Festa event_id 등

    # 원본 데이터 (디버깅/추가 정보용)
    raw_data: dict[str, Any] = field(default_factory=dict)

    # 메타데이터
    fetched_at: datetime | None = None  # 수집 시각

    def to_activity_data(self) -> dict[str, Any]:
        """Activity 저장용 데이터로 변환"""
        return {
            "title": self.title,
            "url": self.url,
            "date": self.date,
            "organizer": self.organizer,
            "description": self.description,
            "source_type": self.source_type,
            "categories": self.categories,
            "themes": self.tags,  # tags를 themes로 매핑
            "external_id": self.external_id,
            "raw_data": self.raw_data,
            "source": "대외",
            "channel": "데스크리서치",
        }


class BaseSeminarCollector(ABC):
    """
    세미나 수집기 기본 클래스

    모든 외부 소스 수집기는 이 클래스를 상속받아 구현
    """

    def __init__(self, name: str):
        """
        Args:
            name: 수집기 이름 (로깅용)
        """
        self.name = name

    @abstractmethod
    async def fetch_seminars(
        self,
        keywords: list[str] | None = None,
        categories: list[str] | None = None,
        limit: int = 50,
        **kwargs,
    ) -> list[SeminarInfo]:
        """
        세미나 정보 수집

        Args:
            keywords: 필터링할 키워드 목록
            categories: 필터링할 카테고리 목록
            limit: 최대 수집 개수
            **kwargs: 소스별 추가 파라미터

        Returns:
            list[SeminarInfo]: 수집된 세미나 목록
        """
        pass

    def filter_by_keywords(
        self,
        seminars: list[SeminarInfo],
        keywords: list[str],
    ) -> list[SeminarInfo]:
        """
        키워드로 필터링

        제목 또는 설명에 키워드가 포함된 세미나만 반환

        Args:
            seminars: 세미나 목록
            keywords: 필터 키워드

        Returns:
            list[SeminarInfo]: 필터링된 세미나 목록
        """
        if not keywords:
            return seminars

        filtered = []
        keywords_lower = [k.lower() for k in keywords]

        for seminar in seminars:
            text = f"{seminar.title} {seminar.description or ''}".lower()
            if any(kw in text for kw in keywords_lower):
                filtered.append(seminar)

        return filtered

    def filter_by_date_range(
        self,
        seminars: list[SeminarInfo],
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[SeminarInfo]:
        """
        날짜 범위로 필터링

        Args:
            seminars: 세미나 목록
            start_date: 시작 날짜 (YYYY-MM-DD)
            end_date: 종료 날짜 (YYYY-MM-DD)

        Returns:
            list[SeminarInfo]: 필터링된 세미나 목록
        """
        if not start_date and not end_date:
            return seminars

        filtered = []

        for seminar in seminars:
            if not seminar.date:
                continue

            try:
                seminar_date = datetime.strptime(seminar.date, "%Y-%m-%d")

                if start_date:
                    start = datetime.strptime(start_date, "%Y-%m-%d")
                    if seminar_date < start:
                        continue

                if end_date:
                    end = datetime.strptime(end_date, "%Y-%m-%d")
                    if seminar_date > end:
                        continue

                filtered.append(seminar)
            except ValueError:
                # 날짜 파싱 실패 시 포함
                filtered.append(seminar)

        return filtered

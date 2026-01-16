"""
Vectorize MVP 유스케이스 (P0)

Vector는 "정확한 답"이 아니라 발굴/추천/정리(탐지·중복·클러스터링)에서 가치가 큼

MVP 3개 유스케이스:
1. 신규 Signal 중복/유사 탐지
2. Entity Linking 고도화 (이름 기반 → 임베딩 기반)
3. Play/Topic 추천

권장 패턴:
- Vectorize는 "후보 생성기" 역할만
- 최종 사실/정답은 Postgres/Graph에서 재검증

인덱스 구조 추천:
- signal_index: Signal+Brief 텍스트 임베딩
- entity_index: Organization/Technology/Topic 임베딩
- evidence_index: Evidence 본문 chunk 임베딩 (선택)

메타데이터 키 (Vectorize 제한: 최대 10개 metadata index):
- entity_type, channel, status, play_id, created_at_bucket, recency_bucket
"""

import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import structlog

from .client import VectorizeClient

logger = structlog.get_logger()


class VectorIndexType(Enum):
    """벡터 인덱스 유형"""

    SIGNAL = "signal"  # Signal + Brief
    ENTITY = "entity"  # Organization, Technology, Topic
    EVIDENCE = "evidence"  # Evidence 본문 chunk


@dataclass
class DuplicateCandidate:
    """중복 후보"""

    signal_id: str
    score: float  # 유사도 점수 (0~1)
    title: str | None = None
    status: str | None = None
    play_id: str | None = None

    def to_dict(self) -> dict:
        return {
            "signal_id": self.signal_id,
            "score": self.score,
            "title": self.title,
            "status": self.status,
            "play_id": self.play_id,
        }


@dataclass
class EntityLinkCandidate:
    """Entity Linking 후보"""

    entity_id: str
    entity_type: str
    name: str
    score: float
    properties: dict | None = None

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "name": self.name,
            "score": self.score,
            "properties": self.properties,
        }


@dataclass
class PlayRecommendation:
    """Play 추천"""

    play_id: str
    score: float
    similar_signals: list[str] = field(default_factory=list)
    success_count: int = 0  # Pilot/Validation 성공 수

    def to_dict(self) -> dict:
        return {
            "play_id": self.play_id,
            "score": self.score,
            "similar_signals": self.similar_signals,
            "success_count": self.success_count,
        }


class VectorizeUseCases:
    """
    Vectorize MVP 유스케이스

    Vectorize는 "후보 생성기" 역할만 하고,
    최종 사실/정답은 Postgres/Graph에서 재검증
    """

    def __init__(self):
        # 인덱스별 클라이언트
        self.signal_client = VectorizeClient(
            index_name=os.getenv("VECTORIZE_SIGNAL_INDEX", "ax-discovery-signals")
        )
        self.entity_client = VectorizeClient(
            index_name=os.getenv("VECTORIZE_ENTITY_INDEX", "ax-discovery-entities")
        )
        self.evidence_client = VectorizeClient(
            index_name=os.getenv("VECTORIZE_EVIDENCE_INDEX", "ax-discovery-evidence")
        )

    # ===== 유스케이스 1: 신규 Signal 중복/유사 탐지 =====

    async def detect_similar_signals(
        self,
        embedding: list[float],
        top_k: int = 5,
        min_similarity: float = 0.8,
        exclude_ids: list[str] | None = None,
        channel_filter: str | None = None,
        play_id_filter: str | None = None,
    ) -> list[DuplicateCandidate]:
        """
        신규 Signal 중복/유사 탐지

        새 Signal 생성 시:
        1. Signal 텍스트 → 임베딩 생성
        2. Vectorize topK → 유사 Signal 후보 반환
        3. 운영적으로 "중복 병합" 또는 "같은 기회 묶음" 생성

        Args:
            embedding: Signal 텍스트 임베딩 (OpenAI 1536d)
            top_k: 반환할 후보 수
            min_similarity: 최소 유사도 임계값
            exclude_ids: 제외할 Signal ID 목록
            channel_filter: 채널 필터
            play_id_filter: Play ID 필터

        Returns:
            유사 Signal 후보 목록
        """
        if not self.signal_client.is_configured:
            logger.warning("Signal Vectorize 인덱스가 설정되지 않았습니다")
            return []

        # 필터 구성
        filter_conditions: dict[str, Any] = {
            "entity_type": {"$eq": "Signal"},
        }
        if channel_filter:
            filter_conditions["channel"] = {"$eq": channel_filter}
        if play_id_filter:
            filter_conditions["play_id"] = {"$eq": play_id_filter}

        try:
            matches = await self.signal_client.query(
                vector=embedding,
                top_k=top_k + (len(exclude_ids) if exclude_ids else 0),
                filter=filter_conditions,
                return_metadata=True,
            )

            candidates = []
            for match in matches:
                # 제외 ID 필터링
                if exclude_ids and match.id in exclude_ids:
                    continue

                # 최소 유사도 필터링
                if match.score < min_similarity:
                    continue

                candidate = DuplicateCandidate(
                    signal_id=match.id,
                    score=match.score,
                    title=match.metadata.name if match.metadata else None,
                    status=match.metadata.extra.get("status") if match.metadata else None,
                    play_id=match.metadata.extra.get("play_id") if match.metadata else None,
                )
                candidates.append(candidate)

                if len(candidates) >= top_k:
                    break

            logger.info(
                "유사 Signal 탐지 완료",
                candidate_count=len(candidates),
                min_similarity=min_similarity,
            )

            return candidates

        except Exception as e:
            logger.error("유사 Signal 탐지 실패", error=str(e))
            return []

    # ===== 유스케이스 2: Entity Linking 고도화 =====

    async def find_entity_candidates(
        self,
        text: str,
        embedding: list[float],
        entity_types: list[str] | None = None,
        top_k: int = 5,
        min_similarity: float = 0.7,
    ) -> list[EntityLinkCandidate]:
        """
        Entity Linking 후보 검색

        이름 유사도 기반은 약어/별칭/오탈자에 취약
        임베딩 기반으로 Customer/Technology/Competitor 후보를 찾고,
        최종 확정은 규칙+검증으로

        Args:
            text: 원본 텍스트 (멘션)
            embedding: 텍스트 임베딩
            entity_types: 검색할 엔티티 타입 목록
            top_k: 반환할 후보 수
            min_similarity: 최소 유사도

        Returns:
            Entity Linking 후보 목록
        """
        if not self.entity_client.is_configured:
            logger.warning("Entity Vectorize 인덱스가 설정되지 않았습니다")
            return []

        # 필터 구성
        filter_conditions: dict[str, Any] = {}
        if entity_types:
            # Vectorize는 $in 필터 지원
            filter_conditions["entity_type"] = {"$in": entity_types}

        try:
            matches = await self.entity_client.query(
                vector=embedding,
                top_k=top_k,
                filter=filter_conditions if filter_conditions else None,
                return_metadata=True,
            )

            candidates = []
            for match in matches:
                if match.score < min_similarity:
                    continue

                candidate = EntityLinkCandidate(
                    entity_id=match.id,
                    entity_type=match.metadata.entity_type if match.metadata else "",
                    name=match.metadata.name if match.metadata else "",
                    score=match.score,
                    properties=match.metadata.extra if match.metadata else None,
                )
                candidates.append(candidate)

            logger.info(
                "Entity Linking 후보 검색 완료",
                text=text[:50],
                candidate_count=len(candidates),
            )

            return candidates

        except Exception as e:
            logger.error("Entity Linking 후보 검색 실패", error=str(e))
            return []

    async def find_organization_by_alias(
        self,
        alias: str,
        embedding: list[float],
        top_k: int = 3,
    ) -> list[EntityLinkCandidate]:
        """
        별칭으로 Organization 찾기

        "삼전" → "삼성전자", "KT" → "KT" 등
        임베딩 기반으로 후보 찾고 규칙으로 최종 확정
        """
        return await self.find_entity_candidates(
            text=alias,
            embedding=embedding,
            entity_types=["Organization", "Customer", "Competitor"],
            top_k=top_k,
            min_similarity=0.6,  # 별칭이므로 임계값 낮춤
        )

    # ===== 유스케이스 3: Play/Topic 추천 =====

    async def recommend_plays(
        self,
        signal_embedding: list[float],
        top_k: int = 3,
        success_only: bool = True,
    ) -> list[PlayRecommendation]:
        """
        Play/Topic 추천

        Signal/Brief 임베딩 → 유사한 과거 성공 Pilot/Validation의 Play/Topic 추천

        Args:
            signal_embedding: Signal 임베딩
            top_k: 반환할 추천 수
            success_only: 성공 사례만 참조할지

        Returns:
            Play 추천 목록
        """
        if not self.signal_client.is_configured:
            logger.warning("Signal Vectorize 인덱스가 설정되지 않았습니다")
            return []

        # 성공 사례 필터 (PILOT_READY, VALIDATED)
        filter_conditions: dict[str, Any] = {
            "entity_type": {"$eq": "Signal"},
        }
        if success_only:
            filter_conditions["status"] = {"$in": ["PILOT_READY", "VALIDATED"]}

        try:
            matches = await self.signal_client.query(
                vector=signal_embedding,
                top_k=top_k * 5,  # 더 많이 조회 후 집계
                filter=filter_conditions,
                return_metadata=True,
            )

            # Play별 집계
            play_scores: dict[str, PlayRecommendation] = {}

            for match in matches:
                play_id = match.metadata.extra.get("play_id") if match.metadata else None
                if not play_id:
                    continue

                if play_id not in play_scores:
                    play_scores[play_id] = PlayRecommendation(
                        play_id=play_id,
                        score=0.0,
                        similar_signals=[],
                        success_count=0,
                    )

                rec = play_scores[play_id]
                rec.score = max(rec.score, match.score)  # 최고 유사도
                rec.similar_signals.append(match.id)
                rec.success_count += 1

            # 점수순 정렬
            recommendations = sorted(
                play_scores.values(),
                key=lambda r: (r.score, r.success_count),
                reverse=True,
            )[:top_k]

            logger.info(
                "Play 추천 완료",
                recommendation_count=len(recommendations),
            )

            return recommendations

        except Exception as e:
            logger.error("Play 추천 실패", error=str(e))
            return []

    # ===== 인덱스 관리 =====

    async def index_signal(
        self,
        signal_id: str,
        embedding: list[float],
        title: str,
        status: str,
        channel: str,
        play_id: str,
        created_at: datetime | None = None,
    ) -> bool:
        """
        Signal을 벡터 인덱스에 저장

        메타데이터 키 (Vectorize 제한 고려):
        - entity_type, status, channel, play_id, created_at_bucket
        """
        if not self.signal_client.is_configured:
            return False

        # created_at_bucket: 월별 버킷 (예: "2026-01")
        bucket = created_at.strftime("%Y-%m") if created_at else datetime.now(UTC).strftime("%Y-%m")

        try:
            await self.signal_client.upsert(
                [
                    {
                        "id": signal_id,
                        "values": embedding,
                        "metadata": {
                            "entity_type": "Signal",
                            "name": title[:200],  # 이름 길이 제한
                            "status": status,
                            "channel": channel,
                            "play_id": play_id,
                            "created_at_bucket": bucket,
                        },
                    }
                ]
            )
            return True
        except Exception as e:
            logger.error("Signal 인덱싱 실패", signal_id=signal_id, error=str(e))
            return False

    async def index_entity(
        self,
        entity_id: str,
        entity_type: str,
        name: str,
        embedding: list[float],
        properties: dict | None = None,
    ) -> bool:
        """
        Entity를 벡터 인덱스에 저장
        """
        if not self.entity_client.is_configured:
            return False

        metadata = {
            "entity_type": entity_type,
            "name": name[:200],
            "confidence": 1.0,
        }
        if properties:
            # 주요 속성만 메타데이터에 포함 (10KiB 제한)
            for key in ["industry", "canonical_name", "aliases"]:
                if key in properties:
                    metadata[key] = properties[key]

        try:
            await self.entity_client.upsert(
                [
                    {
                        "id": entity_id,
                        "values": embedding,
                        "metadata": metadata,
                    }
                ]
            )
            return True
        except Exception as e:
            logger.error("Entity 인덱싱 실패", entity_id=entity_id, error=str(e))
            return False

    async def remove_from_index(
        self,
        ids: list[str],
        index_type: VectorIndexType = VectorIndexType.SIGNAL,
    ) -> bool:
        """
        벡터 인덱스에서 삭제
        """
        client = {
            VectorIndexType.SIGNAL: self.signal_client,
            VectorIndexType.ENTITY: self.entity_client,
            VectorIndexType.EVIDENCE: self.evidence_client,
        }.get(index_type, self.signal_client)

        if not client.is_configured:
            return False

        try:
            await client.delete(ids)
            return True
        except Exception as e:
            logger.error("벡터 삭제 실패", ids=ids, error=str(e))
            return False


# 싱글톤 인스턴스
vectorize_use_cases = VectorizeUseCases()

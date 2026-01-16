"""
Ontology Service

Entity/Triple 생성 시 자동 인덱싱 훅을 포함한 비즈니스 로직 레이어
"""

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models.entity import Entity, EntityType
from backend.database.models.triple import PredicateType, Triple
from backend.database.repositories.ontology import ontology_repo
from backend.services.rag_service import rag_service

logger = structlog.get_logger()


class OntologyService:
    """
    온톨로지 서비스

    Entity/Triple CRUD + 자동 벡터 인덱싱 훅 제공
    """

    def __init__(self, auto_index: bool = True) -> None:
        """
        Args:
            auto_index: Entity 생성 시 자동 벡터 인덱싱 여부 (기본: True)
        """
        self.auto_index = auto_index
        self.repo = ontology_repo

    # ==================== Entity CRUD with Auto-Indexing ====================

    async def create_entity(
        self,
        db: AsyncSession,
        entity_type: EntityType,
        name: str,
        description: str | None = None,
        properties: dict | None = None,
        external_ref_id: str | None = None,
        confidence: float = 1.0,
        created_by: str | None = None,
        auto_index: bool | None = None,
    ) -> Entity:
        """
        Entity 생성 + 자동 인덱싱

        Args:
            db: 데이터베이스 세션
            entity_type: Entity 타입
            name: Entity 이름
            description: 설명
            properties: 추가 속성
            external_ref_id: 외부 참조 ID
            confidence: 신뢰도 (0.0 ~ 1.0)
            created_by: 생성자
            auto_index: 자동 인덱싱 여부 (None이면 서비스 기본값 사용)

        Returns:
            생성된 Entity
        """
        # 1. Entity 생성
        entity = await self.repo.create_entity(
            db=db,
            entity_type=entity_type,
            name=name,
            description=description,
            properties=properties,
            external_ref_id=external_ref_id,
            confidence=confidence,
            created_by=created_by,
        )

        # 2. 자동 인덱싱
        should_index = auto_index if auto_index is not None else self.auto_index

        if should_index:
            await self._index_entity(db, entity)

        return entity

    async def create_entity_batch(
        self,
        db: AsyncSession,
        entities_data: list[dict],
        auto_index: bool | None = None,
    ) -> list[Entity]:
        """
        Entity 배치 생성 + 자동 인덱싱

        Args:
            db: 데이터베이스 세션
            entities_data: Entity 데이터 리스트
                [{"entity_type": ..., "name": ..., ...}, ...]
            auto_index: 자동 인덱싱 여부

        Returns:
            생성된 Entity 리스트
        """
        entities = []

        for data in entities_data:
            entity = await self.repo.create_entity(
                db=db,
                entity_type=data["entity_type"],
                name=data["name"],
                description=data.get("description"),
                properties=data.get("properties"),
                external_ref_id=data.get("external_ref_id"),
                confidence=data.get("confidence", 1.0),
                created_by=data.get("created_by"),
            )
            entities.append(entity)

        # 배치 인덱싱
        should_index = auto_index if auto_index is not None else self.auto_index

        if should_index and entities:
            await self._index_entities_batch(db, entities)

        return entities

    async def update_entity(
        self,
        db: AsyncSession,
        entity_id: str,
        reindex: bool = True,
        **kwargs,
    ) -> Entity | None:
        """
        Entity 업데이트 + 재인덱싱

        Args:
            db: 데이터베이스 세션
            entity_id: Entity ID
            reindex: 인덱스 업데이트 여부 (기본: True)
            **kwargs: 업데이트할 필드

        Returns:
            업데이트된 Entity
        """
        entity = await self.repo.update_entity(db, entity_id, **kwargs)

        if entity and reindex:
            # name, description, properties 중 하나라도 변경되면 재인덱싱
            index_fields = {"name", "description", "properties"}
            if index_fields & set(kwargs.keys()):
                await self._index_entity(db, entity)

        return entity

    async def delete_entity(
        self,
        db: AsyncSession,
        entity_id: str,
        remove_from_index: bool = True,
    ) -> bool:
        """
        Entity 삭제 + 인덱스 제거

        Args:
            db: 데이터베이스 세션
            entity_id: Entity ID
            remove_from_index: 인덱스에서도 제거 여부

        Returns:
            삭제 성공 여부
        """
        # 인덱스에서 먼저 제거
        if remove_from_index:
            await rag_service.remove_from_index(entity_id)

        return await self.repo.delete_entity(db, entity_id)

    # ==================== Triple CRUD ====================

    async def create_triple(
        self,
        db: AsyncSession,
        subject_id: str,
        predicate: PredicateType,
        object_id: str,
        weight: float = 1.0,
        confidence: float = 1.0,
        evidence_ids: list[str] | None = None,
        reasoning_path_id: str | None = None,
        properties: dict | None = None,
        created_by: str | None = None,
    ) -> Triple:
        """
        Triple 생성

        Args:
            db: 데이터베이스 세션
            subject_id: Subject Entity ID
            predicate: 관계 타입
            object_id: Object Entity ID
            weight: 관계 강도 (0.0 ~ 1.0)
            confidence: 신뢰도
            evidence_ids: 증거 ID 리스트
            reasoning_path_id: 추론 경로 ID
            properties: 추가 속성
            created_by: 생성자

        Returns:
            생성된 Triple
        """
        return await self.repo.create_triple(
            db=db,
            subject_id=subject_id,
            predicate=predicate,
            object_id=object_id,
            weight=weight,
            confidence=confidence,
            evidence_ids=evidence_ids,
            reasoning_path_id=reasoning_path_id,
            properties=properties,
            created_by=created_by,
        )

    async def delete_triple(
        self,
        db: AsyncSession,
        triple_id: str,
    ) -> bool:
        """Triple 삭제"""
        return await self.repo.delete_triple(db, triple_id)

    # ==================== Signal Convenience Methods ====================

    async def create_signal_entity(
        self,
        db: AsyncSession,
        signal_id: str,
        title: str,
        pain: str,
        proposed_value: str | None = None,
        customer_segment: str | None = None,
        confidence: float = 1.0,
        created_by: str | None = None,
        auto_index: bool | None = None,
    ) -> Entity:
        """
        Signal Entity 생성 (편의 메서드)

        Args:
            db: 데이터베이스 세션
            signal_id: Signal ID (external_ref_id로 저장)
            title: Signal 제목
            pain: Pain point
            proposed_value: 제안 가치
            customer_segment: 고객 세그먼트
            confidence: 신뢰도
            created_by: 생성자
            auto_index: 자동 인덱싱 여부

        Returns:
            생성된 Signal Entity
        """
        properties = {
            "pain": pain,
        }
        if proposed_value:
            properties["proposed_value"] = proposed_value
        if customer_segment:
            properties["customer_segment"] = customer_segment

        return await self.create_entity(
            db=db,
            entity_type=EntityType.SIGNAL,
            name=title,
            description=f"Pain: {pain}",
            properties=properties,
            external_ref_id=signal_id,
            confidence=confidence,
            created_by=created_by,
            auto_index=auto_index,
        )

    async def create_topic_entity(
        self,
        db: AsyncSession,
        name: str,
        description: str | None = None,
        parent_topic_id: str | None = None,
        created_by: str | None = None,
        auto_index: bool | None = None,
    ) -> Entity:
        """
        Topic Entity 생성 (편의 메서드)

        Args:
            db: 데이터베이스 세션
            name: Topic 이름
            description: 설명
            parent_topic_id: 상위 Topic ID (계층 구조용)
            created_by: 생성자
            auto_index: 자동 인덱싱 여부

        Returns:
            생성된 Topic Entity
        """
        properties = {}
        if parent_topic_id:
            properties["parent_topic_id"] = parent_topic_id

        entity = await self.create_entity(
            db=db,
            entity_type=EntityType.TOPIC,
            name=name,
            description=description,
            properties=properties,
            created_by=created_by,
            auto_index=auto_index,
        )

        # 부모-자식 관계 생성
        if parent_topic_id:
            await self.create_triple(
                db=db,
                subject_id=parent_topic_id,
                predicate=PredicateType.PARENT_OF,
                object_id=entity.entity_id,
                created_by=created_by,
            )

        return entity

    async def create_evidence_entity(
        self,
        db: AsyncSession,
        title: str,
        evidence_type: str,
        source_url: str | None = None,
        content_summary: str | None = None,
        credibility: float = 1.0,
        created_by: str | None = None,
        auto_index: bool | None = None,
    ) -> Entity:
        """
        Evidence Entity 생성 (편의 메서드)

        Args:
            db: 데이터베이스 세션
            title: Evidence 제목
            evidence_type: 증거 유형 (MARKET_DATA, REPORT, INTERVIEW 등)
            source_url: 출처 URL
            content_summary: 내용 요약
            credibility: 신뢰도 (0.0 ~ 1.0)
            created_by: 생성자
            auto_index: 자동 인덱싱 여부

        Returns:
            생성된 Evidence Entity
        """
        properties = {
            "evidence_type": evidence_type,
        }
        if source_url:
            properties["source_url"] = source_url

        return await self.create_entity(
            db=db,
            entity_type=EntityType.EVIDENCE,
            name=title,
            description=content_summary,
            properties=properties,
            confidence=credibility,
            created_by=created_by,
            auto_index=auto_index,
        )

    # ==================== Private Methods ====================

    async def _index_entity(self, db: AsyncSession, entity: Entity) -> bool:
        """
        단일 Entity 인덱싱 (내부용)

        RAG 서비스가 설정되지 않은 경우 조용히 스킵
        """
        if not rag_service.is_configured:
            logger.debug(
                "RAG 서비스 미설정 - 인덱싱 스킵",
                entity_id=entity.entity_id,
            )
            return False

        try:
            success = await rag_service.index_entity(db, entity, update_db=True)

            if success:
                logger.info(
                    "Entity 자동 인덱싱 완료",
                    entity_id=entity.entity_id,
                    entity_type=entity.entity_type.value,
                )
            else:
                logger.warning(
                    "Entity 자동 인덱싱 실패",
                    entity_id=entity.entity_id,
                )

            return success

        except Exception as e:
            logger.error(
                "Entity 인덱싱 오류",
                entity_id=entity.entity_id,
                error=str(e),
            )
            return False

    async def _index_entities_batch(
        self,
        db: AsyncSession,
        entities: list[Entity],
    ) -> dict:
        """
        Entity 배치 인덱싱 (내부용)
        """
        if not rag_service.is_configured:
            logger.debug("RAG 서비스 미설정 - 배치 인덱싱 스킵")
            return {"success": 0, "failed": 0, "skipped": len(entities)}

        try:
            result = await rag_service.index_entities_batch(db, entities)

            logger.info(
                "Entity 배치 자동 인덱싱 완료",
                success=result["success"],
                failed=result["failed"],
                total=result["total"],
            )

            return result

        except Exception as e:
            logger.error("배치 인덱싱 오류", error=str(e))
            return {"success": 0, "failed": len(entities), "total": len(entities)}


# 싱글톤 인스턴스 (자동 인덱싱 활성화)
ontology_service = OntologyService(auto_index=True)

# 인덱싱 비활성화 인스턴스 (필요시 사용)
ontology_service_no_index = OntologyService(auto_index=False)

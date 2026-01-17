"""
RAG (Retrieval-Augmented Generation) Service

벡터 기반 검색 및 컨텍스트 생성 서비스
"""

from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models.entity import Entity, EntityType
from backend.database.repositories.ontology import ontology_repo
from backend.integrations.cloudflare_vectorize import vectorize_client
from backend.services.embedding_service import embedding_service

logger = structlog.get_logger()


class RAGService:
    """
    RAG (Retrieval-Augmented Generation) 서비스

    Entity 임베딩 생성, 벡터 검색, 중복 탐지, 컨텍스트 생성 기능 제공
    """

    def __init__(self) -> None:
        self.embedding = embedding_service
        self.vectorize = vectorize_client

    @property
    def is_configured(self) -> bool:
        """서비스가 설정되었는지 확인"""
        return self.embedding.is_configured and self.vectorize.is_configured

    # ==================== Indexing ====================

    async def index_entity(
        self,
        db: AsyncSession,
        entity: Entity,
        update_db: bool = True,
    ) -> bool:
        """
        Entity를 벡터 인덱스에 추가

        Args:
            db: 데이터베이스 세션
            entity: 인덱싱할 Entity
            update_db: DB에 임베딩 저장 여부

        Returns:
            성공 여부
        """
        if not self.is_configured:
            logger.warning("RAG 서비스가 설정되지 않았습니다")
            return False

        try:
            # 1. Entity → 텍스트 변환
            text = self.embedding.create_entity_text(entity)

            # 2. 임베딩 생성
            embedding_vector = await self.embedding.generate_embedding(text)

            # 3. PostgreSQL에 임베딩 저장 (백업)
            if update_db:
                await ontology_repo.update_entity(
                    db,
                    entity.entity_id,
                    embedding=embedding_vector,
                )

            # 4. Vectorize에 저장
            await self.vectorize.upsert(
                [
                    {
                        "id": entity.entity_id,
                        "values": embedding_vector,
                        "metadata": {
                            "entity_type": entity.entity_type.value,
                            "name": entity.name,
                            "confidence": entity.confidence,
                            "external_ref_id": entity.external_ref_id,
                        },
                    }
                ]
            )

            logger.info(
                "Entity 인덱싱 완료",
                entity_id=entity.entity_id,
                entity_type=entity.entity_type.value,
            )

            return True

        except Exception as e:
            logger.error(
                "Entity 인덱싱 실패",
                entity_id=entity.entity_id,
                error=str(e),
            )
            return False

    async def index_entities_batch(
        self,
        db: AsyncSession,
        entities: list[Entity],
    ) -> dict:
        """
        여러 Entity를 배치로 인덱싱

        Args:
            db: 데이터베이스 세션
            entities: 인덱싱할 Entity 리스트

        Returns:
            인덱싱 결과 요약
        """
        if not self.is_configured:
            logger.warning("RAG 서비스가 설정되지 않았습니다")
            return {"success": 0, "failed": len(entities), "total": len(entities)}

        if not entities:
            return {"success": 0, "failed": 0, "total": 0}

        try:
            # 1. 텍스트 변환
            texts = [self.embedding.create_entity_text(e) for e in entities]

            # 2. 배치 임베딩 생성
            embeddings = await self.embedding.generate_batch(texts)

            # 3. Vectorize에 배치 저장
            vectors = [
                {
                    "id": entity.entity_id,
                    "values": embedding,
                    "metadata": {
                        "entity_type": entity.entity_type.value,
                        "name": entity.name,
                        "confidence": entity.confidence,
                        "external_ref_id": entity.external_ref_id,
                    },
                }
                for entity, embedding in zip(entities, embeddings, strict=True)
            ]

            await self.vectorize.upsert(vectors)

            # 4. DB 업데이트 (각 Entity의 embedding 필드)
            for entity, embedding in zip(entities, embeddings, strict=True):
                await ontology_repo.update_entity(
                    db,
                    entity.entity_id,
                    embedding=embedding,
                )

            logger.info(
                "배치 인덱싱 완료",
                count=len(entities),
            )

            return {"success": len(entities), "failed": 0, "total": len(entities)}

        except Exception as e:
            logger.error(
                "배치 인덱싱 실패",
                error=str(e),
            )
            return {"success": 0, "failed": len(entities), "total": len(entities)}

    async def remove_from_index(self, entity_id: str) -> bool:
        """
        Entity를 벡터 인덱스에서 제거

        Args:
            entity_id: 제거할 Entity ID

        Returns:
            성공 여부
        """
        if not self.vectorize.is_configured:
            return False

        try:
            await self.vectorize.delete([entity_id])
            logger.info("인덱스에서 Entity 제거", entity_id=entity_id)
            return True
        except Exception as e:
            logger.error("인덱스 제거 실패", entity_id=entity_id, error=str(e))
            return False

    # ==================== Search ====================

    async def search_similar(
        self,
        query: str,
        entity_types: list[EntityType] | None = None,
        top_k: int = 10,
        min_score: float = 0.7,
        db: AsyncSession | None = None,
    ) -> list[dict]:
        """
        의미 기반 유사도 검색

        Args:
            query: 검색 쿼리 텍스트
            entity_types: 검색할 Entity 타입 (None이면 전체)
            top_k: 반환할 최대 결과 수
            min_score: 최소 유사도 점수 (0.0 ~ 1.0)
            db: 데이터베이스 세션 (상세 정보 조회용)

        Returns:
            검색 결과 리스트 [{entity, score, metadata}, ...]
        """
        if not self.is_configured:
            raise RuntimeError("RAG 서비스가 설정되지 않았습니다")

        # 1. 쿼리 임베딩 생성
        query_embedding = await self.embedding.generate_embedding(query)

        # 2. 필터 구성
        filter_dict: dict[str, Any] | None = None
        if entity_types:
            type_values = [t.value for t in entity_types]
            if len(type_values) == 1:
                filter_dict = {"entity_type": {"$eq": type_values[0]}}
            else:
                filter_dict = {"entity_type": {"$in": type_values}}

        # 3. 벡터 검색
        matches = await self.vectorize.query(
            vector=query_embedding,
            top_k=top_k,
            filter=filter_dict,
        )

        # 4. 점수 필터링 및 결과 구성
        results = []
        for match in matches:
            if match.score < min_score:
                continue

            result = {
                "entity_id": match.id,
                "score": round(match.score, 4),
                "metadata": match.metadata.to_dict() if match.metadata else None,
            }

            # DB에서 상세 정보 조회 (선택적)
            if db:
                entity = await ontology_repo.get_entity(db, match.id)
                if entity:
                    result["entity"] = entity.to_dict()

            results.append(result)

        logger.debug(
            "유사도 검색 완료",
            query_length=len(query),
            result_count=len(results),
        )

        return results

    async def search_by_embedding(
        self,
        embedding: list[float],
        entity_types: list[EntityType] | None = None,
        top_k: int = 10,
        min_score: float = 0.7,
    ) -> list[dict]:
        """
        임베딩 벡터로 직접 검색

        Args:
            embedding: 검색할 임베딩 벡터
            entity_types: 검색할 Entity 타입
            top_k: 반환할 최대 결과 수
            min_score: 최소 유사도 점수

        Returns:
            검색 결과 리스트
        """
        if not self.vectorize.is_configured:
            raise RuntimeError("Vectorize가 설정되지 않았습니다")

        # 필터 구성
        filter_dict2: dict[str, Any] | None = None
        if entity_types:
            type_values = [t.value for t in entity_types]
            if len(type_values) == 1:
                filter_dict2 = {"entity_type": {"$eq": type_values[0]}}
            else:
                filter_dict2 = {"entity_type": {"$in": type_values}}

        # 벡터 검색
        matches = await self.vectorize.query(
            vector=embedding,
            top_k=top_k,
            filter=filter_dict2,
        )

        # 결과 구성
        results = []
        for match in matches:
            if match.score >= min_score:
                results.append(
                    {
                        "entity_id": match.id,
                        "score": round(match.score, 4),
                        "metadata": match.metadata.to_dict() if match.metadata else None,
                    }
                )

        return results

    # ==================== Duplicate Detection ====================

    async def find_duplicates(
        self,
        text: str,
        entity_type: EntityType = EntityType.SIGNAL,
        threshold: float = 0.85,
        exclude_ids: list[str] | None = None,
    ) -> list[dict]:
        """
        중복 Entity 탐지

        Args:
            text: 중복 검사할 텍스트
            entity_type: 검사 대상 Entity 타입
            threshold: 중복 판정 임계값 (0.0 ~ 1.0)
            exclude_ids: 제외할 Entity ID 리스트

        Returns:
            중복 후보 리스트 [{entity_id, score, metadata}, ...]
        """
        if not self.is_configured:
            logger.warning("RAG 서비스가 설정되지 않았습니다")
            return []

        try:
            results = await self.search_similar(
                query=text,
                entity_types=[entity_type],
                top_k=10,
                min_score=threshold,
            )

            # 제외 ID 필터링
            if exclude_ids:
                results = [r for r in results if r["entity_id"] not in exclude_ids]

            logger.debug(
                "중복 탐지 완료",
                text_length=len(text),
                duplicate_count=len(results),
                threshold=threshold,
            )

            return results

        except Exception as e:
            logger.error("중복 탐지 실패", error=str(e))
            return []

    async def check_signal_duplicate(
        self,
        title: str,
        pain: str,
        proposed_value: str | None = None,
        customer_segment: str | None = None,
        threshold: float = 0.85,
        exclude_signal_id: str | None = None,
    ) -> dict:
        """
        Signal 중복 검사

        Args:
            title: Signal 제목
            pain: Pain point
            proposed_value: 제안 가치
            customer_segment: 고객 세그먼트
            threshold: 중복 판정 임계값
            exclude_signal_id: 제외할 Signal ID (자기 자신)

        Returns:
            {is_duplicate, similar_signals, highest_score}
        """
        # Signal 텍스트 생성
        signal_text = self.embedding.create_signal_text(
            title=title,
            pain=pain,
            proposed_value=proposed_value,
            customer_segment=customer_segment,
        )

        exclude_ids = [exclude_signal_id] if exclude_signal_id else None

        duplicates = await self.find_duplicates(
            text=signal_text,
            entity_type=EntityType.SIGNAL,
            threshold=threshold,
            exclude_ids=exclude_ids,
        )

        highest_score = max([d["score"] for d in duplicates], default=0.0)

        return {
            "is_duplicate": len(duplicates) > 0,
            "similar_signals": duplicates,
            "highest_score": highest_score,
            "threshold": threshold,
        }

    # ==================== Context Generation ====================

    async def generate_context(
        self,
        query: str,
        entity_types: list[EntityType] | None = None,
        max_tokens: int = 4000,
        top_k: int = 10,
        db: AsyncSession | None = None,
    ) -> str:
        """
        RAG Context 생성 (LLM 입력용)

        Args:
            query: 검색 쿼리
            entity_types: 검색할 Entity 타입
            max_tokens: 최대 토큰 수
            top_k: 검색할 최대 결과 수
            db: 데이터베이스 세션

        Returns:
            LLM에 전달할 컨텍스트 문자열
        """
        if not self.is_configured:
            return ""

        # 1. 관련 Entity 검색
        results = await self.search_similar(
            query=query,
            entity_types=entity_types,
            top_k=top_k,
            min_score=0.6,  # Context 생성은 더 넓은 범위
            db=db,
        )

        if not results:
            return ""

        # 2. 토큰 예산 내에서 Context 조립
        context_parts = []
        current_tokens = 0

        for result in results:
            metadata = result.get("metadata", {})
            entity = result.get("entity", {})

            # Context 파트 생성
            entity_type = metadata.get("entity_type", "Unknown")
            name = metadata.get("name", "")
            description = entity.get("description", "") if entity else ""

            part = f"[{entity_type}] {name}"
            if description:
                part += f"\n{description}"
            part += f"\n(유사도: {result['score']:.2f})"

            # 토큰 추정
            part_tokens = self.embedding.estimate_tokens(part)

            if current_tokens + part_tokens > max_tokens:
                break

            context_parts.append(part)
            current_tokens += part_tokens

        context = "\n\n---\n\n".join(context_parts)

        logger.debug(
            "Context 생성 완료",
            query_length=len(query),
            context_parts=len(context_parts),
            estimated_tokens=current_tokens,
        )

        return context

    async def generate_context_for_signal(
        self,
        signal_id: str,
        db: AsyncSession,
        max_tokens: int = 4000,
    ) -> str:
        """
        Signal에 대한 관련 Context 생성

        Args:
            signal_id: Signal ID
            db: 데이터베이스 세션
            max_tokens: 최대 토큰 수

        Returns:
            Signal 관련 컨텍스트 문자열
        """
        # Signal Entity 조회
        entity = await ontology_repo.get_entity_by_external_ref(db, signal_id)
        if not entity:
            return ""

        # Signal 텍스트로 Context 생성
        signal_text = self.embedding.create_entity_text(entity)

        return await self.generate_context(
            query=signal_text,
            entity_types=[
                EntityType.TOPIC,
                EntityType.CUSTOMER,
                EntityType.TECHNOLOGY,
                EntityType.EVIDENCE,
            ],
            max_tokens=max_tokens,
            db=db,
        )

    # ==================== Health Check ====================

    async def health_check(self) -> dict:
        """
        서비스 상태 확인

        Returns:
            {embedding: bool, vectorize: bool, overall: bool}
        """
        embedding_ok = self.embedding.is_configured
        vectorize_ok = (
            await self.vectorize.health_check() if self.vectorize.is_configured else False
        )

        return {
            "embedding": embedding_ok,
            "vectorize": vectorize_ok,
            "overall": embedding_ok and vectorize_ok,
        }


# 싱글톤 인스턴스
rag_service = RAGService()

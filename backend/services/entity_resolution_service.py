"""
Entity Resolution Service

동일 엔티티 식별 및 병합 서비스
LLM과 규칙 기반 매칭을 조합하여 중복 엔티티 처리
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog
from anthropic import AsyncAnthropic
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models.entity import Entity
from backend.database.models.triple import PredicateType
from backend.database.repositories.ontology import ontology_repo
from backend.services.llm_extraction_service import (
    ExtractedEntity,
    PromptLoader,
)

logger = structlog.get_logger()


# ==================== 데이터 모델 ====================


@dataclass
class EntityMatch:
    """엔티티 매칭 결과"""

    new_entity: ExtractedEntity
    existing_entity: Entity | None
    confidence: float
    rationale: str
    action: str  # "merge", "create", "same_as"


@dataclass
class SameAsPair:
    """불확실한 동일 엔티티 쌍"""

    entity_a: ExtractedEntity | Entity
    entity_b: ExtractedEntity | Entity
    confidence: float
    reason: str


@dataclass
class ResolutionResult:
    """Entity Resolution 결과"""

    matches: list[EntityMatch] = field(default_factory=list)
    uncertain_pairs: list[SameAsPair] = field(default_factory=list)
    merged_count: int = 0
    created_count: int = 0
    same_as_count: int = 0


# ==================== Entity Resolution 서비스 ====================


class EntityResolutionService:
    """
    Entity Resolution 서비스

    신규 추출 엔티티와 기존 DB 엔티티 간 동일성 판단
    - 높은 신뢰도 (≥0.85): 자동 병합
    - 중간 신뢰도 (0.5~0.85): SAME_AS Triple 생성
    - 낮은 신뢰도 (<0.5): 별도 엔티티로 생성
    """

    # 자동 병합 임계값
    AUTO_MERGE_THRESHOLD = 0.85

    # SAME_AS Triple 생성 임계값
    SAME_AS_THRESHOLD = 0.5

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        prompts_dir: Path | None = None,
    ):
        self.client = AsyncAnthropic()
        self.model = model
        self.prompt_loader = PromptLoader(prompts_dir)
        self.logger = logger.bind(service="entity_resolution")

    async def resolve_entities(
        self,
        db: AsyncSession,
        new_entities: list[ExtractedEntity],
    ) -> ResolutionResult:
        """
        신규 엔티티와 기존 엔티티 간 동일성 해결

        Args:
            db: 데이터베이스 세션
            new_entities: 신규 추출된 엔티티 목록

        Returns:
            ResolutionResult: 해결 결과
        """
        self.logger.info("Starting entity resolution", new_count=len(new_entities))

        result = ResolutionResult()

        for new_entity in new_entities:
            # 1. 후보 기존 엔티티 검색
            candidates = await self._find_candidates(db, new_entity)

            if not candidates:
                # 후보 없음 → 새로 생성
                result.matches.append(
                    EntityMatch(
                        new_entity=new_entity,
                        existing_entity=None,
                        confidence=1.0,
                        rationale="기존 엔티티에 유사한 후보 없음",
                        action="create",
                    )
                )
                result.created_count += 1
                continue

            # 2. LLM으로 동일성 판단
            best_match = await self._find_best_match(new_entity, candidates)

            if best_match is None:
                # 매칭 실패 → 새로 생성
                result.matches.append(
                    EntityMatch(
                        new_entity=new_entity,
                        existing_entity=None,
                        confidence=1.0,
                        rationale="후보 중 동일 엔티티 없음",
                        action="create",
                    )
                )
                result.created_count += 1
            elif best_match["confidence"] >= self.AUTO_MERGE_THRESHOLD:
                # 높은 신뢰도 → 자동 병합
                result.matches.append(
                    EntityMatch(
                        new_entity=new_entity,
                        existing_entity=best_match["entity"],
                        confidence=best_match["confidence"],
                        rationale=best_match["rationale"],
                        action="merge",
                    )
                )
                result.merged_count += 1
            elif best_match["confidence"] >= self.SAME_AS_THRESHOLD:
                # 중간 신뢰도 → SAME_AS 관계
                result.matches.append(
                    EntityMatch(
                        new_entity=new_entity,
                        existing_entity=best_match["entity"],
                        confidence=best_match["confidence"],
                        rationale=best_match["rationale"],
                        action="same_as",
                    )
                )
                result.uncertain_pairs.append(
                    SameAsPair(
                        entity_a=new_entity,
                        entity_b=best_match["entity"],
                        confidence=best_match["confidence"],
                        reason=best_match["rationale"],
                    )
                )
                result.same_as_count += 1
            else:
                # 낮은 신뢰도 → 새로 생성
                result.matches.append(
                    EntityMatch(
                        new_entity=new_entity,
                        existing_entity=None,
                        confidence=best_match["confidence"],
                        rationale=f"신뢰도 부족: {best_match['rationale']}",
                        action="create",
                    )
                )
                result.created_count += 1

        self.logger.info(
            "Entity resolution completed",
            merged=result.merged_count,
            created=result.created_count,
            same_as=result.same_as_count,
        )

        return result

    async def create_same_as_triples(
        self,
        db: AsyncSession,
        uncertain_pairs: list[SameAsPair],
        created_by: str | None = None,
    ) -> list[str]:
        """
        불확실한 쌍에 대해 SAME_AS Triple 생성

        Args:
            db: 데이터베이스 세션
            uncertain_pairs: 불확실한 동일 엔티티 쌍
            created_by: 생성자

        Returns:
            생성된 Triple ID 목록
        """
        triple_ids = []

        for pair in uncertain_pairs:
            # 엔티티 ID 추출
            if isinstance(pair.entity_a, ExtractedEntity):
                # 아직 생성되지 않은 엔티티 → 스킵 (caller가 먼저 생성해야 함)
                continue
            if isinstance(pair.entity_b, ExtractedEntity):
                continue

            subject_id = pair.entity_a.entity_id
            object_id = pair.entity_b.entity_id

            # 중복 체크
            existing, _ = await ontology_repo.query_triples(
                db,
                subject_id=subject_id,
                predicate=PredicateType.SAME_AS,
                object_id=object_id,
                limit=1,
            )

            if existing:
                self.logger.debug(
                    "SAME_AS triple already exists",
                    subject=subject_id,
                    object=object_id,
                )
                continue

            # Triple 생성 (PROPOSED 상태)
            triple = await ontology_repo.create_triple(
                db=db,
                subject_id=subject_id,
                predicate=PredicateType.SAME_AS,
                object_id=object_id,
                confidence=pair.confidence,
                properties={"reason": pair.reason},
                created_by=created_by,
            )

            # status를 PROPOSED로 유지 (기본값)
            triple_ids.append(triple.triple_id)

            self.logger.info(
                "SAME_AS triple created",
                triple_id=triple.triple_id,
                subject=subject_id,
                object=object_id,
                confidence=pair.confidence,
            )

        return triple_ids

    async def _find_candidates(
        self,
        db: AsyncSession,
        new_entity: ExtractedEntity,
    ) -> list[Entity]:
        """후보 기존 엔티티 검색"""
        # 1. 동일 타입의 엔티티 중 이름이 유사한 것 검색
        candidates: list[Entity] = []

        # 이름 기반 검색 (부분 일치)
        name_parts = new_entity.name.split()
        conditions = [Entity.name.ilike(f"%{part}%") for part in name_parts if len(part) >= 2]

        if conditions:
            query = (
                select(Entity)
                .where(Entity.entity_type == new_entity.entity_type)
                .where(or_(*conditions))
                .limit(10)
            )
            result = await db.execute(query)
            candidates.extend(result.scalars().all())

        # 2. aliases 검색 (properties.aliases에 포함된 경우)
        for alias in new_entity.aliases:
            query = (
                select(Entity)
                .where(Entity.entity_type == new_entity.entity_type)
                .where(Entity.name.ilike(f"%{alias}%"))
                .limit(5)
            )
            result = await db.execute(query)
            for entity in result.scalars().all():
                if entity not in candidates:
                    candidates.append(entity)

        return candidates[:10]  # 최대 10개

    async def _find_best_match(
        self,
        new_entity: ExtractedEntity,
        candidates: list[Entity],
    ) -> dict[str, Any] | None:
        """LLM으로 최적 매칭 찾기"""
        if not candidates:
            return None

        prompts = self.prompt_loader.load("entity-resolution")

        # 엔티티 목록 생성
        entities_json = json.dumps(
            [
                {"name": new_entity.name, "type": new_entity.entity_type.value},
                *[{"name": c.name, "type": c.entity_type.value} for c in candidates],
            ],
            ensure_ascii=False,
            indent=2,
        )

        user_prompt = prompts["user_template"].replace("{entities}", entities_json)
        user_prompt = user_prompt.replace("{context}", "")

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[{"role": "user", "content": user_prompt}],
                system=prompts["system"],
            )

            # TextBlock 타입 가드 (hasattr 사용으로 mock 호환)
            first_block = response.content[0]
            content = first_block.text if hasattr(first_block, "text") else ""
            result = self._parse_json_response(content)

            # same_as_groups에서 new_entity와 매칭되는 그룹 찾기
            for group in result.get("same_as_groups", []):
                canonical = group.get("canonical_name", "")
                members = [m["name"] for m in group.get("members", [])]

                # new_entity가 그룹에 포함되어 있는지 확인
                all_names = [canonical] + members
                if new_entity.name in all_names:
                    # 매칭되는 기존 엔티티 찾기
                    for candidate in candidates:
                        if candidate.name in all_names:
                            return {
                                "entity": candidate,
                                "confidence": group.get("confidence", 0.8),
                                "rationale": group.get("rationale", "LLM 매칭"),
                            }

            # uncertain_pairs에서 찾기
            for pair in result.get("uncertain_pairs", []):
                entity_a_name = pair.get("entity_a", {}).get("name", "")
                entity_b_name = pair.get("entity_b", {}).get("name", "")

                if new_entity.name in [entity_a_name, entity_b_name]:
                    # 매칭되는 기존 엔티티 찾기
                    target_name = (
                        entity_b_name if entity_a_name == new_entity.name else entity_a_name
                    )
                    for candidate in candidates:
                        if candidate.name == target_name:
                            return {
                                "entity": candidate,
                                "confidence": pair.get("confidence", 0.6),
                                "rationale": pair.get("reason", "불확실한 매칭"),
                            }

            return None

        except Exception as e:
            self.logger.warning("LLM matching failed", error=str(e))
            # 폴백: 규칙 기반 매칭
            return await self._rule_based_match(new_entity, candidates)

    async def _rule_based_match(
        self,
        new_entity: ExtractedEntity,
        candidates: list[Entity],
    ) -> dict[str, Any] | None:
        """규칙 기반 매칭 (폴백)"""
        best_match = None
        best_score = 0.0

        for candidate in candidates:
            score = self._calculate_similarity(new_entity, candidate)
            if score > best_score:
                best_score = score
                best_match = candidate

        if best_match and best_score >= 0.5:
            return {
                "entity": best_match,
                "confidence": best_score,
                "rationale": "규칙 기반 이름 유사도 매칭",
            }

        return None

    def _calculate_similarity(
        self,
        new_entity: ExtractedEntity,
        existing: Entity,
    ) -> float:
        """이름 유사도 계산 (간단한 구현)"""
        name1 = new_entity.name.lower().strip()
        name2 = existing.name.lower().strip()

        # 정확히 일치
        if name1 == name2:
            return 1.0

        # 포함 관계
        if name1 in name2 or name2 in name1:
            return 0.8

        # aliases 체크
        for alias in new_entity.aliases:
            if alias.lower() == name2:
                return 0.9
            if alias.lower() in name2 or name2 in alias.lower():
                return 0.7

        # 단어 겹침 비율
        words1 = set(name1.split())
        words2 = set(name2.split())

        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    def _parse_json_response(self, content: str) -> dict[str, Any]:
        """LLM 응답에서 JSON 파싱"""
        import re

        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        json_str = json_match.group(1).strip() if json_match else content.strip()

        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return {"same_as_groups": [], "uncertain_pairs": []}


# 싱글톤 인스턴스
entity_resolution_service = EntityResolutionService()

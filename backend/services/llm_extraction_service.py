"""
LLM Extraction Service

LLM을 활용한 엔티티/관계 추출 서비스
프롬프트 파일을 로드하고 Claude API를 호출하여 BD 문서에서 온톨로지 요소 추출
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog
from anthropic import AsyncAnthropic

from backend.database.models.entity import EntityType
from backend.database.models.triple import PredicateType

logger = structlog.get_logger()


# ==================== 데이터 모델 ====================


@dataclass
class EvidenceSpan:
    """근거 텍스트 위치"""

    start: int
    end: int
    text: str


@dataclass
class ExtractedEntity:
    """LLM이 추출한 엔티티"""

    name: str
    entity_type: EntityType
    aliases: list[str] = field(default_factory=list)
    description: str | None = None
    confidence: float = 0.85
    evidence_span: EvidenceSpan | None = None
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractedRelation:
    """LLM이 추출한 관계"""

    subject: str
    subject_type: EntityType
    predicate: PredicateType
    object: str
    object_type: EntityType
    confidence: float = 0.85
    evidence_span: EvidenceSpan | None = None
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractionResult:
    """추출 결과"""

    entities: list[ExtractedEntity] = field(default_factory=list)
    relations: list[ExtractedRelation] = field(default_factory=list)
    extraction_notes: str | None = None


# ==================== 프롬프트 로더 ====================


class PromptLoader:
    """프롬프트 파일 로더"""

    def __init__(self, prompts_dir: Path | None = None):
        if prompts_dir is None:
            # 기본 경로: .claude/prompts/
            prompts_dir = Path(__file__).parent.parent.parent / ".claude" / "prompts"
        self.prompts_dir = prompts_dir
        self._cache: dict[str, dict[str, str]] = {}

    def load(self, prompt_name: str) -> dict[str, str]:
        """프롬프트 파일 로드 및 파싱

        Args:
            prompt_name: 프롬프트 이름 (예: "entity-extraction")

        Returns:
            {"system": "시스템 프롬프트", "user_template": "사용자 템플릿"}
        """
        if prompt_name in self._cache:
            return self._cache[prompt_name]

        prompt_path = self.prompts_dir / f"{prompt_name}.md"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

        content = prompt_path.read_text(encoding="utf-8")

        # System Prompt 추출
        system_prompt = self._extract_section(content, "System Prompt")

        # User Prompt Template 추출
        user_template = self._extract_section(content, "User Prompt Template")

        result = {
            "system": system_prompt,
            "user_template": user_template,
        }

        self._cache[prompt_name] = result
        return result

    def _extract_section(self, content: str, section_name: str) -> str:
        """마크다운에서 특정 섹션의 코드 블록 추출"""
        import re

        # ## Section Name 다음의 ``` 블록 찾기
        pattern = rf"## {re.escape(section_name)}\s*\n+```[^\n]*\n(.*?)```"
        match = re.search(pattern, content, re.DOTALL)

        if match:
            return match.group(1).strip()

        return ""


# ==================== EntityType/PredicateType 변환 ====================


def parse_entity_type(type_str: str) -> EntityType:
    """문자열을 EntityType으로 변환"""
    type_map = {
        "Activity": EntityType.ACTIVITY,
        "Signal": EntityType.SIGNAL,
        "Topic": EntityType.TOPIC,
        "Scorecard": EntityType.SCORECARD,
        "Brief": EntityType.BRIEF,
        "Validation": EntityType.VALIDATION,
        "Pilot": EntityType.PILOT,
        "Organization": EntityType.ORGANIZATION,
        "Person": EntityType.PERSON,
        "Team": EntityType.TEAM,
        "Technology": EntityType.TECHNOLOGY,
        "Industry": EntityType.INDUSTRY,
        "MarketSegment": EntityType.MARKET_SEGMENT,
        "Trend": EntityType.TREND,
        "Evidence": EntityType.EVIDENCE,
        "Source": EntityType.SOURCE,
        "ReasoningStep": EntityType.REASONING_STEP,
        "Decision": EntityType.DECISION,
        "Play": EntityType.PLAY,
        "Meeting": EntityType.MEETING,
        "Task": EntityType.TASK,
        "Milestone": EntityType.MILESTONE,
        "Customer": EntityType.CUSTOMER,
        "Competitor": EntityType.COMPETITOR,
    }
    return type_map.get(type_str, EntityType.TOPIC)


def parse_predicate_type(predicate_str: str) -> PredicateType:
    """문자열을 PredicateType으로 변환"""
    predicate_map = {
        "GENERATES": PredicateType.GENERATES,
        "EVALUATES_TO": PredicateType.EVALUATES_TO,
        "SUMMARIZED_IN": PredicateType.SUMMARIZED_IN,
        "VALIDATED_BY": PredicateType.VALIDATED_BY,
        "PILOTS_AS": PredicateType.PILOTS_AS,
        "PROGRESSES_TO": PredicateType.PROGRESSES_TO,
        "HAS_PAIN": PredicateType.HAS_PAIN,
        "SIMILAR_TO": PredicateType.SIMILAR_TO,
        "PARENT_OF": PredicateType.PARENT_OF,
        "ADDRESSES": PredicateType.ADDRESSES,
        "TARGETS": PredicateType.TARGETS,
        "EMPLOYS": PredicateType.EMPLOYS,
        "PARTNERS_WITH": PredicateType.PARTNERS_WITH,
        "COMPETES_WITH": PredicateType.COMPETES_WITH,
        "SUBSIDIARY_OF": PredicateType.SUBSIDIARY_OF,
        "IN_INDUSTRY": PredicateType.IN_INDUSTRY,
        "OWNS": PredicateType.OWNS,
        "DECIDES": PredicateType.DECIDES,
        "ATTENDED": PredicateType.ATTENDED,
        "REPORTS_TO": PredicateType.REPORTS_TO,
        "SUPPORTED_BY": PredicateType.SUPPORTED_BY,
        "SOURCED_FROM": PredicateType.SOURCED_FROM,
        "INFERRED_FROM": PredicateType.INFERRED_FROM,
        "CONTRADICTS": PredicateType.CONTRADICTS,
        "BELONGS_TO_PLAY": PredicateType.BELONGS_TO_PLAY,
        "SCHEDULED_FOR": PredicateType.SCHEDULED_FOR,
        "ACHIEVES": PredicateType.ACHIEVES,
        "SAME_AS": PredicateType.SAME_AS,
    }
    return predicate_map.get(predicate_str, PredicateType.RELATED_TO)


# ==================== LLM 추출 서비스 ====================


class LLMExtractionService:
    """
    LLM 기반 엔티티/관계 추출 서비스

    Claude API를 사용하여 BD 문서에서 온톨로지 요소 추출
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        prompts_dir: Path | None = None,
    ):
        self.client = AsyncAnthropic()
        self.model = model
        self.prompt_loader = PromptLoader(prompts_dir)
        self.logger = logger.bind(service="llm_extraction")

    async def extract_entities(self, document: str) -> list[ExtractedEntity]:
        """문서에서 엔티티 추출

        Args:
            document: BD 문서 텍스트

        Returns:
            추출된 엔티티 목록
        """
        self.logger.info("Extracting entities from document", doc_length=len(document))

        prompts = self.prompt_loader.load("entity-extraction")

        user_prompt = prompts["user_template"].replace("{document}", document)

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[{"role": "user", "content": user_prompt}],
                system=prompts["system"],
            )

            # 응답 파싱 (TextBlock 타입 가드: hasattr 사용으로 mock 호환)
            first_block = response.content[0]
            content = first_block.text if hasattr(first_block, "text") else ""
            result = self._parse_json_response(content)

            entities = []
            for entity_data in result.get("entities", []):
                entity = self._parse_entity(entity_data)
                if entity:
                    entities.append(entity)

            self.logger.info("Entities extracted", count=len(entities))
            return entities

        except Exception as e:
            self.logger.error("Entity extraction failed", error=str(e))
            raise

    async def extract_relations(
        self, document: str, entities: list[ExtractedEntity]
    ) -> list[ExtractedRelation]:
        """문서에서 관계 추출

        Args:
            document: BD 문서 텍스트
            entities: 추출된 엔티티 목록

        Returns:
            추출된 관계 목록
        """
        self.logger.info(
            "Extracting relations from document",
            doc_length=len(document),
            entity_count=len(entities),
        )

        prompts = self.prompt_loader.load("relation-extraction")

        # 엔티티 목록을 JSON으로 변환
        entities_json = json.dumps(
            [{"name": e.name, "type": e.entity_type.value} for e in entities],
            ensure_ascii=False,
            indent=2,
        )

        user_prompt = (
            prompts["user_template"]
            .replace("{entities}", entities_json)
            .replace("{document}", document)
        )

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[{"role": "user", "content": user_prompt}],
                system=prompts["system"],
            )

            # TextBlock 타입 가드 (hasattr 사용으로 mock 호환)
            first_block = response.content[0]
            content = first_block.text if hasattr(first_block, "text") else ""
            result = self._parse_json_response(content)

            relations = []
            for relation_data in result.get("relations", []):
                relation = self._parse_relation(relation_data)
                if relation:
                    relations.append(relation)

            self.logger.info("Relations extracted", count=len(relations))
            return relations

        except Exception as e:
            self.logger.error("Relation extraction failed", error=str(e))
            raise

    async def extract_all(self, document: str) -> ExtractionResult:
        """문서에서 엔티티와 관계 모두 추출

        Args:
            document: BD 문서 텍스트

        Returns:
            추출 결과 (엔티티 + 관계)
        """
        self.logger.info("Starting full extraction", doc_length=len(document))

        # 1. 엔티티 추출
        entities = await self.extract_entities(document)

        # 2. 관계 추출 (엔티티 기반)
        relations = await self.extract_relations(document, entities)

        result = ExtractionResult(
            entities=entities,
            relations=relations,
            extraction_notes=f"Extracted {len(entities)} entities and {len(relations)} relations",
        )

        self.logger.info(
            "Full extraction completed",
            entities=len(entities),
            relations=len(relations),
        )

        return result

    def _parse_json_response(self, content: str) -> dict[str, Any]:
        """LLM 응답에서 JSON 파싱"""
        import re

        # JSON 블록 추출 (```json ... ```)
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        json_str = json_match.group(1).strip() if json_match else content.strip()

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            self.logger.warning("JSON parse failed, attempting fix", error=str(e))
            # 기본값 반환
            return {"entities": [], "relations": []}

    def _parse_entity(self, data: dict[str, Any]) -> ExtractedEntity | None:
        """엔티티 데이터 파싱"""
        try:
            evidence_span = None
            if "evidence_span" in data and data["evidence_span"]:
                span_data = data["evidence_span"]
                evidence_span = EvidenceSpan(
                    start=span_data.get("start", 0),
                    end=span_data.get("end", 0),
                    text=span_data.get("text", ""),
                )

            return ExtractedEntity(
                name=data["name"],
                entity_type=parse_entity_type(data.get("type", "Topic")),
                aliases=data.get("aliases", []),
                description=data.get("description"),
                confidence=data.get("confidence", 0.85),
                evidence_span=evidence_span,
                properties=data.get("properties", {}),
            )
        except Exception as e:
            self.logger.warning("Entity parse failed", error=str(e), data=data)
            return None

    def _parse_relation(self, data: dict[str, Any]) -> ExtractedRelation | None:
        """관계 데이터 파싱"""
        try:
            evidence_span = None
            if "evidence_span" in data and data["evidence_span"]:
                span_data = data["evidence_span"]
                evidence_span = EvidenceSpan(
                    start=span_data.get("start", 0),
                    end=span_data.get("end", 0),
                    text=span_data.get("text", ""),
                )

            return ExtractedRelation(
                subject=data["subject"],
                subject_type=parse_entity_type(data.get("subject_type", "Topic")),
                predicate=parse_predicate_type(data.get("predicate", "RELATED_TO")),
                object=data["object"],
                object_type=parse_entity_type(data.get("object_type", "Topic")),
                confidence=data.get("confidence", 0.85),
                evidence_span=evidence_span,
                properties=data.get("properties", {}),
            )
        except Exception as e:
            self.logger.warning("Relation parse failed", error=str(e), data=data)
            return None


# 싱글톤 인스턴스
llm_extraction_service = LLMExtractionService()

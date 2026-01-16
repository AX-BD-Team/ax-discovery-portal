"""
Embedding Service

텍스트 임베딩 생성 서비스 (OpenAI API 사용)
"""

import os

import httpx
import structlog

from backend.database.models.entity import Entity, EntityType

logger = structlog.get_logger()


class EmbeddingService:
    """
    텍스트 임베딩 생성 서비스

    OpenAI text-embedding-3-small 모델을 사용하여 텍스트를 벡터로 변환합니다.
    """

    # 지원하는 임베딩 모델 설정
    MODELS = {
        "text-embedding-3-small": {"dimension": 1536, "max_tokens": 8191},
        "text-embedding-3-large": {"dimension": 3072, "max_tokens": 8191},
    }

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        api_key: str | None = None,
    ) -> None:
        """
        Args:
            model: 임베딩 모델 이름
            api_key: OpenAI API 키 (미지정 시 환경변수 사용)
        """
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.base_url = "https://api.openai.com/v1"

        if model not in self.MODELS:
            raise ValueError(f"지원하지 않는 모델: {model}. 지원 모델: {list(self.MODELS.keys())}")

        self.dimension = self.MODELS[model]["dimension"]
        self.max_tokens = self.MODELS[model]["max_tokens"]

        self._validate_config()

    def _validate_config(self) -> None:
        """설정 유효성 검사"""
        if not self.api_key:
            logger.warning(
                "OpenAI API 키 미설정",
                message="OPENAI_API_KEY 환경변수를 설정하세요. 임베딩 기능이 비활성화됩니다.",
            )

    @property
    def is_configured(self) -> bool:
        """서비스가 설정되었는지 확인"""
        return bool(self.api_key)

    @property
    def headers(self) -> dict[str, str]:
        """API 요청 헤더"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def generate_embedding(self, text: str) -> list[float]:
        """
        단일 텍스트 임베딩 생성

        Args:
            text: 임베딩할 텍스트

        Returns:
            임베딩 벡터 (float 리스트)

        Raises:
            RuntimeError: API 호출 실패 시
        """
        if not self.is_configured:
            raise RuntimeError("OpenAI API 키가 설정되지 않았습니다")

        if not text or not text.strip():
            raise ValueError("임베딩할 텍스트가 비어있습니다")

        # 텍스트 정규화 (줄바꿈을 공백으로)
        normalized_text = text.replace("\n", " ").strip()

        logger.debug(
            "임베딩 생성 요청",
            model=self.model,
            text_length=len(normalized_text),
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/embeddings",
                headers=self.headers,
                json={
                    "model": self.model,
                    "input": normalized_text,
                    "encoding_format": "float",
                },
            )

            if response.status_code != 200:
                error_detail = response.text[:500]
                logger.error(
                    "OpenAI API 오류",
                    status_code=response.status_code,
                    response=error_detail,
                )
                raise RuntimeError(f"OpenAI API 오류 ({response.status_code}): {error_detail}")

            result = response.json()
            embedding = result["data"][0]["embedding"]

            logger.debug(
                "임베딩 생성 완료",
                dimension=len(embedding),
                usage=result.get("usage", {}),
            )

            return embedding

    async def generate_batch(
        self,
        texts: list[str],
        batch_size: int = 100,
    ) -> list[list[float]]:
        """
        배치 텍스트 임베딩 생성

        Args:
            texts: 임베딩할 텍스트 리스트
            batch_size: 한 번에 처리할 텍스트 수 (최대 2048)

        Returns:
            임베딩 벡터 리스트
        """
        if not self.is_configured:
            raise RuntimeError("OpenAI API 키가 설정되지 않았습니다")

        if not texts:
            return []

        # 빈 텍스트 필터링
        valid_texts = [t.replace("\n", " ").strip() for t in texts if t and t.strip()]
        if not valid_texts:
            raise ValueError("유효한 텍스트가 없습니다")

        logger.info(
            "배치 임베딩 생성 시작",
            total_texts=len(valid_texts),
            batch_size=batch_size,
        )

        all_embeddings: list[list[float]] = []

        # 배치 단위로 처리
        for i in range(0, len(valid_texts), batch_size):
            batch = valid_texts[i : i + batch_size]

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    headers=self.headers,
                    json={
                        "model": self.model,
                        "input": batch,
                        "encoding_format": "float",
                    },
                )

                if response.status_code != 200:
                    logger.error(
                        "배치 임베딩 API 오류",
                        batch_index=i // batch_size,
                        status_code=response.status_code,
                    )
                    raise RuntimeError(f"OpenAI API 오류: {response.text[:500]}")

                result = response.json()

                # 결과는 index 순서대로 정렬되어 있음
                batch_embeddings = [item["embedding"] for item in result["data"]]
                all_embeddings.extend(batch_embeddings)

                logger.debug(
                    "배치 임베딩 완료",
                    batch_index=i // batch_size,
                    processed=len(all_embeddings),
                    usage=result.get("usage", {}),
                )

        logger.info(
            "배치 임베딩 생성 완료",
            total_embeddings=len(all_embeddings),
        )

        return all_embeddings

    def create_entity_text(self, entity: Entity) -> str:
        """
        Entity를 임베딩용 텍스트로 변환

        Args:
            entity: 변환할 Entity 객체

        Returns:
            임베딩용 텍스트 문자열
        """
        parts = [
            f"[{entity.entity_type.value}]",
            entity.name,
        ]

        if entity.description:
            parts.append(entity.description)

        # properties에서 추가 컨텍스트 추출
        if entity.properties:
            # Signal인 경우 pain, proposed_value 포함
            if entity.entity_type == EntityType.SIGNAL:
                if pain := entity.properties.get("pain"):
                    parts.append(f"Pain: {pain}")
                if value := entity.properties.get("proposed_value"):
                    parts.append(f"Value: {value}")

            # Customer인 경우 segment 포함
            elif entity.entity_type == EntityType.CUSTOMER:
                if segment := entity.properties.get("segment"):
                    parts.append(f"Segment: {segment}")

            # Technology인 경우 category 포함
            elif entity.entity_type == EntityType.TECHNOLOGY:
                if category := entity.properties.get("category"):
                    parts.append(f"Category: {category}")

        return "\n".join(parts)

    def create_signal_text(
        self,
        title: str,
        pain: str,
        proposed_value: str | None = None,
        customer_segment: str | None = None,
    ) -> str:
        """
        Signal 데이터를 임베딩용 텍스트로 변환

        Args:
            title: Signal 제목
            pain: Pain point
            proposed_value: 제안 가치
            customer_segment: 고객 세그먼트

        Returns:
            임베딩용 텍스트 문자열
        """
        parts = [f"[Signal] {title}", f"Pain: {pain}"]

        if proposed_value:
            parts.append(f"Value: {proposed_value}")

        if customer_segment:
            parts.append(f"Customer: {customer_segment}")

        return "\n".join(parts)

    async def compute_similarity(
        self,
        embedding1: list[float],
        embedding2: list[float],
    ) -> float:
        """
        두 임베딩 간 코사인 유사도 계산

        Args:
            embedding1: 첫 번째 임베딩
            embedding2: 두 번째 임베딩

        Returns:
            코사인 유사도 (0.0 ~ 1.0)
        """
        if len(embedding1) != len(embedding2):
            raise ValueError("임베딩 차원이 일치하지 않습니다")

        # 코사인 유사도 계산
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2, strict=True))
        norm1 = sum(a * a for a in embedding1) ** 0.5
        norm2 = sum(b * b for b in embedding2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = dot_product / (norm1 * norm2)

        # -1 ~ 1 범위를 0 ~ 1로 정규화
        return (similarity + 1) / 2

    def estimate_tokens(self, text: str) -> int:
        """
        텍스트의 토큰 수 추정 (대략적)

        Args:
            text: 토큰 수를 추정할 텍스트

        Returns:
            추정 토큰 수
        """
        # 영어: ~4자당 1토큰, 한글: ~2자당 1토큰
        # 보수적으로 2자당 1토큰으로 추정
        return len(text) // 2


# 싱글톤 인스턴스
embedding_service = EmbeddingService()

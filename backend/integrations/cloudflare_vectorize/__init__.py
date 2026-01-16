"""
Cloudflare Vectorize 통합 모듈

벡터 검색을 위한 Cloudflare Vectorize API 클라이언트

P0 MVP 유스케이스:
1. 신규 Signal 중복/유사 탐지
2. Entity Linking 고도화 (이름 기반 → 임베딩 기반)
3. Play/Topic 추천

권장 패턴:
- Vectorize는 "후보 생성기" 역할만
- 최종 사실/정답은 Postgres/Graph에서 재검증
"""

from backend.integrations.cloudflare_vectorize.client import (
    VectorizeClient,
    VectorMatch,
    VectorMetadata,
    vectorize_client,
)
from backend.integrations.cloudflare_vectorize.use_cases import (
    DuplicateCandidate,
    EntityLinkCandidate,
    PlayRecommendation,
    VectorIndexType,
    VectorizeUseCases,
    vectorize_use_cases,
)

__all__ = [
    # Client
    "VectorizeClient",
    "VectorMatch",
    "VectorMetadata",
    "vectorize_client",
    # Use Cases (P0)
    "VectorizeUseCases",
    "vectorize_use_cases",
    "VectorIndexType",
    "DuplicateCandidate",
    "EntityLinkCandidate",
    "PlayRecommendation",
]

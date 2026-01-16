#!/usr/bin/env python3
"""
기존 Entity 배치 인덱싱 스크립트

DB에 저장된 기존 Entity들을 Vectorize에 배치로 인덱싱합니다.

Usage:
    # 모든 Entity 인덱싱
    python scripts/index_entities.py

    # 특정 타입만 인덱싱
    python scripts/index_entities.py --type Signal
    python scripts/index_entities.py --type Signal --type Topic

    # 임베딩이 없는 Entity만 인덱싱
    python scripts/index_entities.py --only-missing

    # Dry run (실제 인덱싱 없이 대상만 확인)
    python scripts/index_entities.py --dry-run

    # 배치 크기 조정
    python scripts/index_entities.py --batch-size 50

환경변수:
    OPENAI_API_KEY: OpenAI API 키 (필수)
    CLOUDFLARE_ACCOUNT_ID: Cloudflare 계정 ID (필수)
    CLOUDFLARE_API_TOKEN: Cloudflare API 토큰 (필수)
    VECTORIZE_INDEX_NAME: Vectorize 인덱스 이름 (기본: ax-discovery-entities)
    DATABASE_URL: PostgreSQL 연결 URL
"""

import argparse
import asyncio
import os
import sys
from datetime import datetime

import structlog
from dotenv import load_dotenv
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

# ruff: noqa: E402
from backend.database.models.entity import Entity, EntityType
from backend.database.session import SessionLocal
from backend.integrations.cloudflare_vectorize import VectorizeClient
from backend.services.embedding_service import EmbeddingService

# 로거 설정
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(colors=True),
    ]
)
logger = structlog.get_logger()


class EntityIndexer:
    """Entity 배치 인덱싱 클래스"""

    def __init__(
        self,
        batch_size: int = 100,
        dry_run: bool = False,
    ) -> None:
        self.batch_size = batch_size
        self.dry_run = dry_run
        self.embedding_service = EmbeddingService()
        self.vectorize_client = VectorizeClient()

        # 통계
        self.stats = {
            "total": 0,
            "processed": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0,
        }

    async def validate_services(self) -> bool:
        """서비스 설정 검증"""
        errors = []

        if not self.embedding_service.is_configured:
            errors.append("OPENAI_API_KEY가 설정되지 않았습니다")

        if not self.vectorize_client.is_configured:
            errors.append("Cloudflare Vectorize 설정이 누락되었습니다 (CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN)")

        if errors:
            for error in errors:
                logger.error(error)
            return False

        # Vectorize 연결 테스트
        if not self.dry_run:
            try:
                is_healthy = await self.vectorize_client.health_check()
                if not is_healthy:
                    logger.error("Vectorize 연결 실패")
                    return False
                logger.info("Vectorize 연결 성공", index=self.vectorize_client.index_name)
            except Exception as e:
                logger.error("Vectorize 연결 테스트 실패", error=str(e))
                return False

        return True

    async def get_entities_to_index(
        self,
        db: AsyncSession,
        entity_types: list[EntityType] | None = None,
        only_missing: bool = False,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Entity]:
        """인덱싱할 Entity 조회"""
        query = select(Entity)

        # 타입 필터
        if entity_types:
            query = query.where(Entity.entity_type.in_(entity_types))

        # 임베딩 없는 것만
        if only_missing:
            query = query.where(Entity.embedding.is_(None))

        # 정렬 및 페이지네이션
        query = query.order_by(Entity.created_at.asc()).offset(offset).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())

    async def count_entities(
        self,
        db: AsyncSession,
        entity_types: list[EntityType] | None = None,
        only_missing: bool = False,
    ) -> int:
        """인덱싱 대상 Entity 수 조회"""
        query = select(func.count()).select_from(Entity)

        if entity_types:
            query = query.where(Entity.entity_type.in_(entity_types))

        if only_missing:
            query = query.where(Entity.embedding.is_(None))

        result = await db.scalar(query)
        return result or 0

    async def index_batch(
        self,
        db: AsyncSession,
        entities: list[Entity],
    ) -> dict:
        """Entity 배치 인덱싱"""
        if not entities:
            return {"success": 0, "failed": 0}

        success = 0
        failed = 0

        try:
            # 1. 텍스트 변환
            texts = []
            valid_entities = []

            for entity in entities:
                try:
                    text = self.embedding_service.create_entity_text(entity)
                    if text.strip():
                        texts.append(text)
                        valid_entities.append(entity)
                    else:
                        logger.warning(
                            "빈 텍스트 - 스킵",
                            entity_id=entity.entity_id,
                        )
                        self.stats["skipped"] += 1
                except Exception as e:
                    logger.warning(
                        "텍스트 변환 실패",
                        entity_id=entity.entity_id,
                        error=str(e),
                    )
                    failed += 1

            if not texts:
                return {"success": 0, "failed": failed}

            # 2. 배치 임베딩 생성
            logger.debug("임베딩 생성 중...", count=len(texts))
            embeddings = await self.embedding_service.generate_batch(texts)

            # 3. Vectorize에 업로드
            vectors = []
            for entity, embedding in zip(valid_entities, embeddings, strict=True):
                vectors.append({
                    "id": entity.entity_id,
                    "values": embedding,
                    "metadata": {
                        "entity_type": entity.entity_type.value,
                        "name": entity.name[:500] if entity.name else "",
                        "confidence": entity.confidence,
                        "external_ref_id": entity.external_ref_id,
                    },
                })

            logger.debug("Vectorize 업로드 중...", count=len(vectors))
            await self.vectorize_client.upsert(vectors)

            # 4. DB 업데이트 (임베딩 필드)
            for entity, embedding in zip(valid_entities, embeddings, strict=True):
                entity.embedding = embedding

            await db.commit()

            success = len(valid_entities)
            logger.info(
                "배치 인덱싱 완료",
                success=success,
                failed=failed,
            )

        except Exception as e:
            logger.error("배치 인덱싱 실패", error=str(e))
            await db.rollback()
            failed = len(entities)

        return {"success": success, "failed": failed}

    async def run(
        self,
        entity_types: list[EntityType] | None = None,
        only_missing: bool = False,
    ) -> dict:
        """배치 인덱싱 실행"""
        start_time = datetime.now()

        logger.info(
            "=" * 60,
        )
        logger.info(
            "Entity 배치 인덱싱 시작",
            entity_types=[t.value for t in entity_types] if entity_types else "ALL",
            only_missing=only_missing,
            batch_size=self.batch_size,
            dry_run=self.dry_run,
        )
        logger.info(
            "=" * 60,
        )

        # 서비스 검증
        if not await self.validate_services():
            return {"error": "서비스 설정 오류"}

        async with SessionLocal() as db:
            # 총 개수 확인
            total = await self.count_entities(db, entity_types, only_missing)
            self.stats["total"] = total

            logger.info(f"인덱싱 대상: {total}개 Entity")

            if total == 0:
                logger.info("인덱싱할 Entity가 없습니다")
                return self.stats

            if self.dry_run:
                logger.info("[DRY RUN] 실제 인덱싱을 수행하지 않습니다")

                # 대상 Entity 샘플 출력
                sample = await self.get_entities_to_index(
                    db, entity_types, only_missing, offset=0, limit=10
                )
                logger.info("대상 Entity 샘플:")
                for entity in sample:
                    logger.info(
                        f"  - {entity.entity_id}: [{entity.entity_type.value}] {entity.name[:50]}..."
                    )

                return self.stats

            # 배치 처리
            offset = 0
            batch_num = 0

            while offset < total:
                batch_num += 1
                logger.info(
                    f"배치 {batch_num} 처리 중... ({offset + 1}-{min(offset + self.batch_size, total)}/{total})"
                )

                # Entity 조회
                entities = await self.get_entities_to_index(
                    db, entity_types, only_missing, offset, self.batch_size
                )

                if not entities:
                    break

                # 인덱싱
                result = await self.index_batch(db, entities)

                self.stats["processed"] += len(entities)
                self.stats["success"] += result["success"]
                self.stats["failed"] += result["failed"]

                offset += self.batch_size

                # 진행률 출력
                progress = (self.stats["processed"] / total) * 100
                logger.info(
                    f"진행률: {progress:.1f}% ({self.stats['processed']}/{total})"
                )

        # 완료
        elapsed = datetime.now() - start_time

        logger.info(
            "=" * 60,
        )
        logger.info(
            "배치 인덱싱 완료",
            total=self.stats["total"],
            processed=self.stats["processed"],
            success=self.stats["success"],
            failed=self.stats["failed"],
            skipped=self.stats["skipped"],
            elapsed=str(elapsed),
        )
        logger.info(
            "=" * 60,
        )

        return self.stats


async def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="기존 Entity를 Vectorize에 배치 인덱싱합니다.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python scripts/index_entities.py                    # 모든 Entity 인덱싱
  python scripts/index_entities.py --type Signal      # Signal만 인덱싱
  python scripts/index_entities.py --only-missing     # 임베딩 없는 것만
  python scripts/index_entities.py --dry-run          # 대상만 확인
        """,
    )

    parser.add_argument(
        "--type",
        "-t",
        action="append",
        dest="types",
        choices=[t.value for t in EntityType],
        help="인덱싱할 Entity 타입 (복수 지정 가능)",
    )

    parser.add_argument(
        "--only-missing",
        "-m",
        action="store_true",
        help="임베딩이 없는 Entity만 인덱싱",
    )

    parser.add_argument(
        "--batch-size",
        "-b",
        type=int,
        default=100,
        help="배치 크기 (기본: 100)",
    )

    parser.add_argument(
        "--dry-run",
        "-d",
        action="store_true",
        help="실제 인덱싱 없이 대상만 확인",
    )

    args = parser.parse_args()

    # Entity 타입 변환
    entity_types = None
    if args.types:
        entity_types = [EntityType(t) for t in args.types]

    # 인덱서 실행
    indexer = EntityIndexer(
        batch_size=args.batch_size,
        dry_run=args.dry_run,
    )

    try:
        stats = await indexer.run(
            entity_types=entity_types,
            only_missing=args.only_missing,
        )

        # 결과 출력
        if "error" in stats:
            sys.exit(1)

        if stats["failed"] > 0:
            logger.warning(f"{stats['failed']}개 Entity 인덱싱 실패")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("사용자에 의해 중단됨")
        sys.exit(130)
    except Exception as e:
        logger.error("인덱싱 실패", error=str(e))
        sys.exit(1)


def cli():
    """CLI 엔트리포인트 (pyproject.toml용)"""
    asyncio.run(main())


if __name__ == "__main__":
    cli()

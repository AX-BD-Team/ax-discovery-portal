"""
기본 CRUD 저장소 패턴

모든 저장소의 베이스 클래스
"""

from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class CRUDBase(Generic[ModelType]):
    """
    기본 CRUD 작업 클래스

    C: Create
    R: Read (get, get_multi)
    U: Update
    D: Delete
    """

    def __init__(self, model: type[ModelType]):
        """
        Args:
            model: SQLAlchemy 모델 클래스
        """
        self.model = model

    async def get(self, db: AsyncSession, id: Any) -> ModelType | None:
        """
        ID로 단일 레코드 조회

        Args:
            db: 데이터베이스 세션
            id: Primary Key 값

        Returns:
            ModelType | None
        """
        # NOTE: 모델별 PK 컬럼명이 다를 수 있음 (signal_id, brief_id 등)
        # 실제 사용 시 하위 클래스에서 get_by_id 메서드를 오버라이드
        result = await db.execute(
            select(self.model).where(self.model.id == id)  # type: ignore[attr-defined]
        )
        return result.scalar_one_or_none()

    async def get_multi(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> list[ModelType]:
        """
        여러 레코드 조회 (페이지네이션)

        Args:
            db: 데이터베이스 세션
            skip: 건너뛸 레코드 수
            limit: 가져올 레코드 수

        Returns:
            list[ModelType]
        """
        result = await db.execute(select(self.model).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def count(self, db: AsyncSession) -> int:
        """
        전체 레코드 수 조회

        Args:
            db: 데이터베이스 세션

        Returns:
            int: 레코드 수
        """
        result = await db.execute(select(func.count()).select_from(self.model))
        return result.scalar() or 0

    async def create(self, db: AsyncSession, obj_in: dict) -> ModelType:
        """
        새 레코드 생성

        Args:
            db: 데이터베이스 세션
            obj_in: 생성할 데이터 (dict)

        Returns:
            ModelType: 생성된 객체
        """
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update(self, db: AsyncSession, db_obj: ModelType, obj_in: dict) -> ModelType:
        """
        레코드 업데이트

        Args:
            db: 데이터베이스 세션
            db_obj: 업데이트할 DB 객체
            obj_in: 업데이트할 데이터 (dict)

        Returns:
            ModelType: 업데이트된 객체
        """
        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, id: Any) -> bool:
        """
        레코드 삭제

        Args:
            db: 데이터베이스 세션
            id: Primary Key 값

        Returns:
            bool: 삭제 성공 여부
        """
        obj = await self.get(db, id)
        if obj:
            await db.delete(obj)
            await db.flush()
            return True
        return False

# repositories/base_repository.py
from typing import TypeVar, Generic, List, Optional, Type, Union, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

# 제네릭 타입 정의
ModelType = TypeVar("ModelType")  # SQLAlchemy 모델
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)  # 생성용 Pydantic 스키마
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)  # 업데이트용 Pydantic 스키마


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        """
        CRUD 기본 기능을 제공하는 Repository 기본 클래스

        Args:
            model: SQLAlchemy 모델 클래스
        """
        self.model = model

    async def get(self, db: AsyncSession, id: int) -> Optional[ModelType]:
        """ID로 단일 레코드 조회"""
        stmt = select(self.model).where(self.model.id == id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi(
            self,
            db: AsyncSession,
            *,
            skip: int = 0,
            limit: int = 100
    ) -> List[ModelType]:
        """여러 레코드 조회 (페이징)"""
        stmt = select(self.model).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType) -> ModelType:
        """새 레코드 생성"""
        obj_data = obj_in.dict()
        db_obj = self.model(**obj_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
            self,
            db: AsyncSession,
            *,
            db_obj: ModelType,
            obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """기존 레코드 업데이트"""
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, *, id: int) -> ModelType:
        """레코드 삭제"""
        stmt = select(self.model).where(self.model.id == id)
        result = await db.execute(stmt)
        obj = result.scalar_one_or_none()
        if obj:
            await db.delete(obj)
            await db.commit()
        return obj

    async def count(self, db: AsyncSession) -> int:
        """총 레코드 수 조회"""
        stmt = select(self.model)
        result = await db.execute(stmt)
        return len(result.scalars().all())

    async def exists(self, db: AsyncSession, id: int) -> bool:
        """레코드 존재 여부 확인"""
        stmt = select(self.model).where(self.model.id == id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none() is not None
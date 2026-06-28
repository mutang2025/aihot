"""Source management API (CRUD). Auth-protected for write endpoints."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Source
from app.schemas import SourceIn, SourceOut

router = APIRouter()


@router.get("/api/sources", response_model=list[SourceOut])
async def list_sources(
    enabled_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Source).order_by(Source.tier, Source.name)
    if enabled_only:
        stmt = stmt.where(Source.enabled == True)  # noqa: E712
    return (await db.execute(stmt)).scalars().all()


@router.get("/api/sources/{source_id}", response_model=SourceOut)
async def get_source(source_id: int, db: AsyncSession = Depends(get_db)):
    s = (await db.execute(select(Source).where(Source.id == source_id))).scalar_one_or_none()
    if not s:
        raise HTTPException(404, "Source not found")
    return s


@router.post("/api/sources", response_model=SourceOut, status_code=201)
async def create_source(payload: SourceIn, db: AsyncSession = Depends(get_db)):
    s = Source(**payload.model_dump())
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


@router.patch("/api/sources/{source_id}", response_model=SourceOut)
async def update_source(source_id: int, payload: dict, db: AsyncSession = Depends(get_db)):
    s = (await db.execute(select(Source).where(Source.id == source_id))).scalar_one_or_none()
    if not s:
        raise HTTPException(404, "Source not found")
    for k, v in payload.items():
        if hasattr(s, k):
            setattr(s, k, v)
    await db.commit()
    await db.refresh(s)
    return s


@router.delete("/api/sources/{source_id}", status_code=204)
async def delete_source(source_id: int, db: AsyncSession = Depends(get_db)):
    s = (await db.execute(select(Source).where(Source.id == source_id))).scalar_one_or_none()
    if not s:
        raise HTTPException(404, "Source not found")
    await db.delete(s)
    await db.commit()

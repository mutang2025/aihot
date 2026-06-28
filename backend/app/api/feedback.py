"""Feedback API for human-in-the-loop scoring refinement."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Feedback
from app.schemas import FeedbackIn

router = APIRouter()


@router.post("/api/feedback", status_code=201)
async def submit_feedback(payload: FeedbackIn, db: AsyncSession = Depends(get_db)):
    f = Feedback(**payload.model_dump())
    db.add(f)
    await db.commit()
    await db.refresh(f)
    return {"id": f.id, "rating": f.rating}

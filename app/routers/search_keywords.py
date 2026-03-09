from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.search_keyword import SearchKeyword
from app.models.user import User
from app.routers.deps import get_current_user
from app.schemas.search_keyword import SearchKeywordCreate, SearchKeywordResponse

router = APIRouter(prefix="/search-keywords", tags=["search-keywords"])


@router.get("", response_model=list[SearchKeywordResponse])
def list_keywords(
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> list[SearchKeyword]:
    return db.query(SearchKeyword).order_by(SearchKeyword.created_at).all()


@router.post("", response_model=SearchKeywordResponse, status_code=status.HTTP_201_CREATED)
def create_keyword(
    body: SearchKeywordCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> SearchKeyword:
    existing = db.query(SearchKeyword).filter(SearchKeyword.keyword == body.keyword).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="このキーワードはすでに登録されています",
        )
    keyword = SearchKeyword(keyword=body.keyword)
    db.add(keyword)
    db.commit()
    db.refresh(keyword)
    return keyword


@router.delete("/{keyword_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_keyword(
    keyword_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> None:
    keyword = db.query(SearchKeyword).filter(SearchKeyword.id == keyword_id).first()
    if not keyword:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="キーワードが見つかりません",
        )
    db.delete(keyword)
    db.commit()

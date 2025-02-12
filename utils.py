from typing import List, TypeVar, Generic
from sqlalchemy.orm import Session
from fastapi import HTTPException

T = TypeVar('T')

def paginate(query, page: int = 1, page_size: int = 10):
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items
    } 
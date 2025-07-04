from pydantic import BaseModel
from typing import Optional, Dict, Any, List, TypeVar, Generic
from uuid import UUID

T = TypeVar('T')


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    field: Optional[str] = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
    status: str = "error"
    request_id: Optional[UUID] = None


class SuccessResponse(BaseModel):
    message: str
    status: str = "success"
    data: Optional[Dict[str, Any]] = None


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    per_page: int
    pages: int
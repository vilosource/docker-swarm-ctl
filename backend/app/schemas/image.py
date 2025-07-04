from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime


class ImageResponse(BaseModel):
    id: str
    tags: List[str]
    created: datetime
    size: int
    labels: Dict[str, str]
    
    class Config:
        from_attributes = True


class ImagePull(BaseModel):
    repository: str = Field(..., description="Image repository")
    tag: str = Field("latest", description="Image tag")
    auth_config: Optional[Dict[str, str]] = Field(None, description="Registry authentication")
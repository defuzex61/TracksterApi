from pydantic import BaseModel
from typing import Optional, List
from src.models.track import TrackResponse

class AlbumCreate(BaseModel):
    title: str

class AlbumResponse(AlbumCreate):
    id: int
    cover_path: Optional[str] = None
    play_count: int = 0
    tracks: List[TrackResponse] = []

class PaginatedAlbumsResponse(BaseModel):
    albums: List[AlbumResponse]
    total: int
    page: int
    limit: int
    total_pages: int
    
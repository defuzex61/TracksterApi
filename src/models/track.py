from pydantic import BaseModel
from typing import List, Optional

class TrackCreate(BaseModel):
    title: str
    genre: Optional[str] = None
    bpm: Optional[int] = None
    key: Optional[str] = None
    author: Optional[str] = None  # Автор трека

class TrackResponse(TrackCreate):
    id: int
    filename: str
    cover_path: Optional[str] = None
    duration: Optional[int] = None  # Длительность в секундах
    play_count: int = 0
    author: Optional[str] = None 
    user_id: str

class PaginatedTracksResponse(BaseModel):
    tracks: List[TrackResponse]
    total: int
    page: int
    limit: int
    total_pages: int
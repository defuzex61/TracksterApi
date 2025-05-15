from pydantic import BaseModel
from typing import Optional, List
from src.models.track import TrackResponse

class PlaylistCreate(BaseModel):
    title: str

class PlaylistResponse(PlaylistCreate):
    id: int
    cover_path: Optional[str] = None
    play_count: int = 0
    tracks: List[TrackResponse] = []

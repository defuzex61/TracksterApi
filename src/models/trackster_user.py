from pydantic import BaseModel
from typing import List, Optional

from src.models.track import TrackResponse
from src.models.album import AlbumResponse

class TracksterUser(BaseModel):
    user_id: str
    username: str
    email: Optional[str] = None
    avatar_path: Optional[str] = None
    bio: Optional[str] = None
    website: Optional[str] = None
    followers_count: int = 0
    tracks_count: int = 0


class TracksterSearchResponse(BaseModel):
    tracks: List[TrackResponse] = []
    albums: List[AlbumResponse] = []
    total_tracks: int = 0
    total_albums: int = 0
    page: int = 1
    limit: int = 20
    total_pages_tracks: int = 0
    total_pages_albums: int = 0
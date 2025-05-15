from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from src.models.playlist import PlaylistCreate, PlaylistResponse
from src.services.playlist_service import create_playlist, get_playlist_details
from src.auth.firebase_auth import get_current_user

router = APIRouter()

@router.post("/playlists", response_model=PlaylistResponse)
async def create_playlist_endpoint(
    title: str = Form(...),
    cover: UploadFile = File(None),  # Добавляем обложку
    track_ids: str = Form(None),
    user: dict = Depends(get_current_user)
):
    track_ids_list = [int(tid) for tid in track_ids.split(",")] if track_ids else None
    return create_playlist(title, cover, user["uid"], track_ids_list)

@router.get("/playlists/{playlist_id}", response_model=PlaylistResponse)
async def get_playlist(playlist_id: int, user: dict = Depends(get_current_user)):
    return get_playlist_details(playlist_id, user["uid"])
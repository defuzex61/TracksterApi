import json
from typing import List
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from src.auth.firebase_auth import get_current_user
from src.db.database import get_user_albums, update_track_cover, upload_album
from src.models.album import AlbumResponse
from pathlib import Path
import os
import mimetypes
from fastapi.responses import FileResponse

from src.services.album_service import get_album_details

router = APIRouter()

@router.post("/albums", response_model=AlbumResponse)
async def upload_album_endpoint(
    title: str = Form(...),
    cover: UploadFile = File(None),
    tracks: List[UploadFile] = File(...),
    tracks_metadata: str = Form(None),
    user: dict = Depends(get_current_user)
):
    # Определяем путь для сохранения обложек
    cover_dir = os.path.join("covers", "album-covers")
    cover_path = None
    if cover:
        # Создаём директорию, если её нет
        os.makedirs(cover_dir, exist_ok=True)
        cover_filename = f"{user['uid']}_{cover.filename}"
        cover_path = os.path.join(cover_dir, cover_filename)
        with open(cover_path, "wb") as f:
            f.write(await cover.read())

    tracks_data = []
    if tracks_metadata:
        try:
            metadata_list = json.loads(tracks_metadata)
            if len(metadata_list) != len(tracks):
                raise HTTPException(status_code=400, detail="Number of tracks and metadata entries must match")
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid tracks_metadata JSON format")
    else:
        metadata_list = [{}] * len(tracks)

    for track, metadata in zip(tracks, metadata_list):
        # Сохраняем треки в uploads (или можешь изменить путь для треков, если нужно)
        track_filename = f"{user['uid']}_{track.filename}"
        track_path = os.path.join("uploads", track_filename)
        os.makedirs("uploads", exist_ok=True)
        with open(track_path, "wb") as f:
            f.write(await track.read())

        tracks_data.append({
            "filename": track_filename,
            "title": metadata.get("title", track.filename.split(".")[0]),
            "genre": metadata.get("genre"),
            "bpm": metadata.get("bpm"),
            "key": metadata.get("key"),
            "author": metadata.get("author", user["uid"]),
            "duration": metadata.get("duration")
        })

    album = upload_album(title=title, user_id=user["uid"], cover_path=cover_path, tracks_data=tracks_data)
    return AlbumResponse(**album)

@router.patch("/tracks/{track_id}/cover")
async def update_track_cover_endpoint(track_id: int, cover_path: str, user: dict = Depends(get_current_user)):
    try:
        updated_track = update_track_cover(track_id=track_id, cover_path=cover_path, user_id=user["uid"])
        return updated_track
    except ValueError as e:
        if "Track not found" in str(e):
            raise HTTPException(status_code=404, detail="Track not found")
        if "Not authorized" in str(e):
            raise HTTPException(status_code=403, detail="Not authorized to update this track")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/covers/{cover_filename}")
async def get_cover(cover_filename: str):
    cover_file_path = Path("covers/album-covers") / cover_filename
    if ".." in cover_filename:
        raise HTTPException(status_code=400, detail="Недопустимое имя файла обложки")
    if not cover_file_path.exists():
        raise HTTPException(status_code=404, detail="Обложка не найдена")
    media_type = mimetypes.guess_type(cover_file_path)[0] or "image/jpeg"
    return FileResponse(cover_file_path, media_type=media_type)


@router.get("/albums/{album_id}", response_model=AlbumResponse)
async def get_album(album_id: int, user: dict = Depends(get_current_user)):
    return get_album_details(album_id, user["uid"])

@router.get("/user/albums", response_model=List[AlbumResponse])
async def get_user_albums_endpoint(user: dict = Depends(get_current_user)):
    try:
        albums = get_user_albums(user["uid"])
        return albums
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch user albums: {str(e)}")
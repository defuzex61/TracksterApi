import os
from src.db.database import save_album, add_track_to_album, get_album_by_id, get_track_by_id, get_album_tracks, upload_album
from fastapi import HTTPException, UploadFile
import shutil

COVER_DIR = "covers"
if not os.path.exists(COVER_DIR):
    os.makedirs(COVER_DIR)

def create_album(title: str, cover: UploadFile | None, user_id: str, track_ids: list[int] | None = None) -> dict:
    cover_path = None
    if cover:
        cover_filename = f"{user_id}_{cover.filename}"
        cover_path = os.path.join(COVER_DIR, cover_filename)
        with open(cover_path, "wb") as buffer:
            shutil.copyfileobj(cover.file, buffer)

    album_id = save_album(title, user_id, cover_path)
    if track_ids:
        for track_id in track_ids:
            add_track_to_album(album_id, track_id)
    
    return {"id": album_id, "title": title, "cover_path": cover_path, "tracks": []}

def get_album_details(album_id: int, user_id: str) -> dict:
    album = get_album_by_id(album_id)
    if not album:
        raise HTTPException(status_code=404, detail="Альбом не найден")
    
    track_ids = get_album_tracks(album_id)
    tracks = [get_track_by_id(track_id) for track_id in track_ids]
    tracks_response = [
        {
            "id": t[0],
            "filename": t[1],
            "title": t[2],
            "genre": t[3],
            "bpm": t[4],
            "key": t[5],
            "user_id": t[6],
            "cover_path": t[7],
            "author": t[8],
            "duration": t[9],
            "play_count": t[10]
        }
        for t in tracks if t
    ]
    
    return {
        "id": album[0],
        "title": album[1],
        "cover_path": album[3],
        "play_count": album[4],
        "tracks": tracks_response
    }

def create_album(title: str, cover: UploadFile | None, user_id: str, track_ids: list[int] | None) -> dict:
    cover_path = None
    if cover:
        os.makedirs(COVER_DIR, exist_ok=True)
        cover_filename = f"{user_id}_{cover.filename}"
        cover_path = os.path.join(COVER_DIR, cover_filename)
        with open(cover_path, "wb") as f:
            f.write(cover.file.read())

    album = upload_album(
        title=title,
        user_id=user_id,
        cover_path=cover_path,
        track_ids=track_ids
    )
    return album
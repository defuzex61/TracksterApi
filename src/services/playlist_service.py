import os
from src.db.database import save_playlist, add_track_to_playlist, get_playlist_by_id, get_track_by_id, get_playlist_tracks
from fastapi import HTTPException, UploadFile
import shutil

COVER_DIR = "covers"
if not os.path.exists(COVER_DIR):
    os.makedirs(COVER_DIR)

def create_playlist(title: str, cover: UploadFile | None, user_id: str, track_ids: list[int] | None = None) -> dict:
    cover_path = None
    if cover:
        cover_filename = f"{user_id}_{cover.filename}"
        cover_path = os.path.join(COVER_DIR, cover_filename)
        with open(cover_path, "wb") as buffer:
            shutil.copyfileobj(cover.file, buffer)
    
    playlist_id = save_playlist(title, user_id, cover_path)
    if track_ids:
        for track_id in track_ids:
            add_track_to_playlist(playlist_id, track_id)
    
    return {"id": playlist_id, "title": title, "cover_path": cover_path, "tracks": []}

def get_playlist_details(playlist_id: int, user_id: str) -> dict:
    playlist = get_playlist_by_id(playlist_id, user_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Плейлист не найден или доступ запрещён")
    
    track_ids = get_playlist_tracks(playlist_id)
    tracks = [get_track_by_id(track_id, user_id) for track_id in track_ids]
    tracks_response = [
        {"id": t[0], "title": t[2], "genre": t[3], "bpm": t[4], "key": t[5], "filename": t[1], "cover_path": t[7], "author": t[8], "duration": t[9]}
        for t in tracks if t
    ]
    
    return {"id": playlist[0], "title": playlist[1], "cover_path": playlist[2], "tracks": tracks_response}
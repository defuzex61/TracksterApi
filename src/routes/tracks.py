import mimetypes
import os
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, Depends, Header, HTTPException
from fastapi.responses import FileResponse
from src.db.database import fetch_most_played_tracks, get_track_by_id, get_tracks_paginated, get_album_by_id, get_album_tracks, get_playlist_by_id, get_playlist_tracks, get_username_by_id, increment_track_play_count, increment_album_play_count, increment_playlist_play_count, log_play, get_play_stats, add_track_to_favorites, remove_track_from_favorites, get_user_favorites, is_track_in_favorites
from src.models.track import PaginatedTracksResponse, TrackCreate, TrackResponse
from src.services.track_service import process_track, get_track_file_path
from src.auth.firebase_auth import get_current_user
from datetime import datetime, timedelta

router = APIRouter()

UPLOAD_DIR = "uploads"
COVER_DIR = "covers"

@router.post("/upload", response_model=TrackResponse)
async def upload_music(
    file: UploadFile = File(...),
    cover: UploadFile = File(None),
    title: str = Form(...),
    genre: str | None = Form(None),
    bpm: int | None = Form(None),
    key: str | None = Form(None),
    user: dict = Depends(get_current_user)
):
    return process_track(file, cover, title, genre, bpm, key, user["uid"])

@router.get("/tracks/{track_id}", response_model=TrackResponse)
async def get_track(track_id: int, user: dict = Depends(get_current_user)):
    track = get_track_by_id(track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Трек не найден или доступ запрещён")
    id, filename, title, genre, bpm, key, user_id, cover_path, author, duration, play_count = track
    
    username = get_username_by_id(author)
    
    return {
        "id": id,
        "title": title,
        "genre": genre,
        "bpm": bpm,
        "key": key,
        "filename": filename,
        "cover_path": cover_path,
        "author": username,
        "user_id": user_id,
        "duration": duration,
        "play_count": play_count
    }

@router.get("/tracks", response_model=PaginatedTracksResponse)
async def get_all_tracks(
    page: int = 1,
    limit: int = 10,
    user: dict = Depends(get_current_user)
):
    tracks, total = get_tracks_paginated(page=page, limit=limit)
    tracks_response = []
    for t in tracks:
        username = get_username_by_id(t[8])  # t[8] — это поле author (user_id)
        track = {
            "id": t[0],
            "title": t[2],
            "genre": t[3],
            "bpm": t[4],
            "key": t[5],
            "filename": t[1],
            "cover_path": t[7],
            "author": username,  # Используем username вместо user_id
            "user_id": t[6],
            "duration": t[9],
            "play_count": t[10]
        }
        tracks_response.append(track)
    
    total_pages = (total + limit - 1) // limit
    return {
        "tracks": tracks_response,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages
    }

@router.get("/stream/{track_id}")
async def stream_track(track_id: int, user: dict = Depends(get_current_user), range: str = Header(default=None)):
    file_path = get_track_file_path(track_id)  
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Track file not found")
    
    # Увеличиваем счётчик прослушиваний и логируем
    increment_track_play_count(track_id)
    log_play(user["uid"], track_id=track_id)
    
    return FileResponse(file_path, headers={"Content-Range": range} if range else None)


@router.get("/covers/{cover_filename}")
async def get_cover(cover_filename: str):
    cover_file_path = Path(COVER_DIR) / cover_filename
    if ".." in cover_filename:
        raise HTTPException(status_code=400, detail="Недопустимое имя файла обложки")
    if not cover_file_path.exists():
        raise HTTPException(status_code=404, detail="Обложка не найдена")
    media_type = mimetypes.guess_type(cover_file_path)[0] or "image/jpeg"
    return FileResponse(cover_file_path, media_type=media_type)

# Новые эндпоинты для альбомов и плейлистов
@router.get("/albums/{album_id}")
async def get_album(album_id: int, user: dict = Depends(get_current_user)):
    # Получаем альбом без проверки владельца
    album = get_album_by_id(album_id)
    if not album:
        raise HTTPException(status_code=404, detail="Альбом не найден")
    id, title, user_id, cover_path, play_count = album
    track_ids = get_album_tracks(album_id)
    tracks = []
    for track_id in track_ids:
        track = get_track_by_id(track_id)
        if track:
            username = get_username_by_id(track[8])  # track[8] — это поле author (user_id)
            tracks.append({
                "id": track[0],
                "title": track[2],
                "genre": track[3],
                "bpm": track[4],
                "key": track[5],
                "filename": track[1],
                "cover_path": track[7],
                "author": username,  # Используем username вместо user_id
                "duration": track[9],
                "play_count": track[10]
            })
    return {
        "id": id,
        "title": title,
        "cover_path": cover_path,
        "play_count": play_count,
        "tracks": tracks
    }

@router.get("/playlists/{playlist_id}")
async def get_playlist(playlist_id: int, user: dict = Depends(get_current_user)):
    # Получаем плейлист без проверки владельца
    playlist = get_playlist_by_id(playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Плейлист не найден")
    id, title, user_id, cover_path, play_count = playlist
    track_ids = get_playlist_tracks(playlist_id)
    tracks = []
    for track_id in track_ids:
        track = get_track_by_id(track_id)
        if track:
            username = get_username_by_id(track[8])  # track[8] — это поле author (user_id)
            tracks.append({
                "id": track[0],
                "title": track[2],
                "genre": track[3],
                "bpm": track[4],
                "key": track[5],
                "filename": track[1],
                "cover_path": track[7],
                "author": username,  # Используем username вместо user_id
                "duration": track[9],
                "play_count": track[10]
            })
    return {
        "id": id,
        "title": title,
        "cover_path": cover_path,
        "play_count": play_count,
        "tracks": tracks
    }

@router.post("/play-album/{album_id}")
async def play_album(album_id: int, user: dict = Depends(get_current_user)):
    # Получаем альбом без проверки владельца
    album = get_album_by_id(album_id)
    if not album:
        raise HTTPException(status_code=404, detail="Альбом не найден")
    
    # Увеличиваем счётчик прослушиваний альбома
    increment_album_play_count(album_id)
    log_play(user["uid"], album_id=album_id)
    
    # Увеличиваем счётчик прослушиваний для каждого трека в альбоме
    track_ids = get_album_tracks(album_id)
    for track_id in track_ids:
        increment_track_play_count(track_id)
        log_play(user["uid"], track_id=track_id)
    
    return {"message": "Альбом воспроизведён"}

@router.post("/play-playlist/{playlist_id}")
async def play_playlist(playlist_id: int, user: dict = Depends(get_current_user)):
    # Получаем плейлист без проверки владельца
    playlist = get_playlist_by_id(playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Плейлист не найден")
    
    # Увеличиваем счётчик прослушиваний плейлиста
    increment_playlist_play_count(playlist_id)
    log_play(user["uid"], playlist_id=playlist_id)
    
    # Увеличиваем счётчик прослушиваний для каждого трека в плейлисте
    track_ids = get_playlist_tracks(playlist_id)
    for track_id in track_ids:
        increment_track_play_count(track_id)
        log_play(user["uid"], track_id=track_id)
    
    return {"message": "Плейлист воспроизведён"}

# Эндпоинт для получения статистики
@router.get("/stats/{entity_type}/{entity_id}")
async def get_stats(
    entity_type: str,  # 'track', 'album', 'playlist'
    entity_id: int,
    period: str = "week",  # 'week', 'month', 'year'
    user: dict = Depends(get_current_user)
):
    # Определяем временной диапазон
    end_date = datetime.now()
    if period == "week":
        start_date = end_date - timedelta(days=7)
    elif period == "month":
        start_date = end_date - timedelta(days=30)
    elif period == "year":
        start_date = end_date - timedelta(days=365)
    else:
        raise HTTPException(status_code=400, detail="Недопустимый период. Используйте 'week', 'month' или 'year'.")

    start_timestamp = int(start_date.timestamp())
    end_timestamp = int(end_date.timestamp())

    # Проверяем, что entity_type допустимый
    if entity_type not in ["track", "album", "playlist"]:
        raise HTTPException(status_code=400, detail="Недопустимый тип сущности. Используйте 'track', 'album' или 'playlist'.")

    # Проверяем, что сущность существует (без проверки владельца)
    if entity_type == "track":
        entity = get_track_by_id(entity_id)
    elif entity_type == "album":
        entity = get_album_by_id(entity_id)
    else:  # playlist
        entity = get_playlist_by_id(entity_id)
    
    if not entity:
        raise HTTPException(status_code=404, detail="Сущность не найдена")

    # Получаем статистику
    stats = get_play_stats(user["uid"], entity_type, entity_id, start_timestamp, end_timestamp)
    
    # Формируем данные для графика
    play_data = [{"date": row[0], "play_count": row[1]} for row in stats]
    return {"stats": play_data}


@router.get("/most-played", response_model=PaginatedTracksResponse)
async def get_most_played_tracks(
    page: int = 1,
    limit: int = 20,
    user: dict = Depends(get_current_user)
):
    tracks, total = fetch_most_played_tracks(page, limit)
    tracks_response = []
    for t in tracks:
        username = get_username_by_id(t[8])  # t[8] — это поле author
        track = {
            "id": t[0],
            "title": t[2],
            "genre": t[3],
            "bpm": t[4],
            "key": t[5],
            "filename": t[1],
            "cover_path": t[7],
            "author": username,
            "user_id": t[6],
            "duration": t[9],
            "play_count": t[10]
        }
        tracks_response.append(track)
    total_pages = (total + limit - 1) // limit
    return {
        "tracks": tracks_response,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages
    }

# Эндпоинты для работы с избранными треками
@router.post("/tracks/{track_id}/like")
async def like_track(track_id: int, user: dict = Depends(get_current_user)):
    track = get_track_by_id(track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Трек не найден")
    
    success = add_track_to_favorites(user["uid"], track_id)
    if success:
        return {"message": "Трек добавлен в избранное"}
    else:
        return {"message": "Трек уже в избранном"}

@router.delete("/tracks/{track_id}/like")
async def unlike_track(track_id: int, user: dict = Depends(get_current_user)):
    track = get_track_by_id(track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Трек не найден")
    
    success = remove_track_from_favorites(user["uid"], track_id)
    if success:
        return {"message": "Трек удален из избранного"}
    else:
        return {"message": "Трек не был в избранном"}

@router.get("/tracks/{track_id}/like/status")
async def check_like_status(track_id: int, user: dict = Depends(get_current_user)):
    track = get_track_by_id(track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Трек не найден")
    
    is_liked = is_track_in_favorites(user["uid"], track_id)
    return {"is_liked": is_liked}

@router.get("/favorites", response_model=PaginatedTracksResponse)
async def get_favorites(
    page: int = 1,
    limit: int = 20,
    user: dict = Depends(get_current_user)
):
    tracks, total = get_user_favorites(user["uid"], page, limit)
    tracks_response = []
    for t in tracks:
        username = get_username_by_id(t[8])  # t[8] — это поле author
        track = {
            "id": t[0],
            "title": t[2],
            "genre": t[3],
            "bpm": t[4],
            "key": t[5],
            "filename": t[1],
            "cover_path": t[7],
            "author": username,
            "user_id": t[6],
            "duration": t[9],
            "play_count": t[10]
        }
        tracks_response.append(track)
    total_pages = (total + limit - 1) // limit
    return {
        "tracks": tracks_response,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages
    }
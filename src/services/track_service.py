import os
import shutil
import subprocess
from fastapi import BackgroundTasks, HTTPException, UploadFile
from src.db.database import get_username_by_id, save_track, get_track_by_id, sync_user
from mutagen.mp3 import MP3  
from firebase_admin import auth

UPLOAD_DIR = "uploads"
COVER_DIR = "covers"

for dir in [UPLOAD_DIR, COVER_DIR]:
    if not os.path.exists(dir):
        os.makedirs(dir)
for dir in [UPLOAD_DIR, COVER_DIR]:
    if not os.path.exists(dir):
        os.makedirs(dir)

def process_track(file: UploadFile, cover: UploadFile | None, title: str, genre: str | None, bpm: int | None, key: str | None, user_id: str) -> dict:
    print(f"Starting process_track for title: {title}, user_id: {user_id}")
    print(f"Audio file: {file.filename}")
    if cover:
        print(f"Cover file: {cover.filename}")
    else:
        print("No cover file provided")

    # Синхронизация пользователя с Firebase
    try:
        firebase_user = auth.get_user(user_id)
        username = firebase_user.display_name if firebase_user.display_name else user_id
        email = firebase_user.email
        sync_user({
            "uid": user_id,
            "display_name": username,
            "email": email
        })
    except Exception as e:
        print(f"Failed to sync user {user_id} with Firebase: {e}")
        username = get_username_by_id(user_id)  # Пробуем взять из базы
    # Если username всё ещё равен user_id, это значит, что пользователь не синхронизирован
    author = username if username != user_id else "Unknown User"

    # Сохранение трека
    original_filename = f"{user_id}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, original_filename)
    print(f"Saving audio file as: {file_path}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Конвертация в MP3, если нужно
    if not file.filename.lower().endswith(".mp3"):
        mp3_filename = original_filename.rsplit(".", 1)[0] + ".mp3"
        mp3_path = os.path.join(UPLOAD_DIR, mp3_filename)
        print(f"Converting audio to MP3: {mp3_path}")
        subprocess.run(["ffmpeg", "-i", file_path, "-acodec", "mp3", mp3_path], check=True)
        os.remove(file_path)
        filename = mp3_filename
        print(f"Audio converted, new filename: {filename}")
    else:
        filename = original_filename
        print(f"Audio already in MP3 format, filename: {filename}")

    # Расчёт длительности
    audio = MP3(os.path.join(UPLOAD_DIR, filename))
    duration = int(audio.info.length)  # Длительность в секундах
    print(f"Calculated duration: {duration} seconds")

    # Сохранение обложки (если есть)
    cover_path = None
    if cover:
        cover_filename = f"{user_id}_{cover.filename}"
        relative_cover_path = os.path.join(COVER_DIR, cover_filename)
        print(f"Saving cover file as: {relative_cover_path}")
        with open(relative_cover_path, "wb") as buffer:
            shutil.copyfileobj(cover.file, buffer)
        cover_path = cover_filename
        print(f"Cover path to be saved in DB: {cover_path}")
    else:
        print("No cover path to save in DB")

    # Сохраняем трек с user_id и username
    print(f"Saving track to database with filename: {filename}, cover_path: {cover_path}, author: {author}")
    track_id = save_track(filename, title, genre, bpm, key, user_id, cover_path, author, duration)
    print(f"Track saved with id: {track_id}")

    # Формируем результат
    result = {
        "id": track_id,
        "title": title,
        "genre": genre,
        "bpm": bpm,
        "key": key,
        "filename": filename,
        "cover_path": cover_path,
        "author": author,  # username
        "duration": duration,
        "play_count": 0,  
        "user_id": user_id  # Добавляем user_id автора
    }
    print(f"Returning result: {result}")
    return result

def get_track_file_path(track_id: int) -> str:
    track = get_track_by_id(track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Трек не найден")
    file_path = os.path.join(UPLOAD_DIR, track[1])  # filename — второй элемент
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Файл не найден")
    return file_path
#async def increment_play_count(track_id: int):
    background_tasks = BackgroundTasks()
    background_tasks.add_task(update_play_count_in_database, track_id)
    return background_tasks

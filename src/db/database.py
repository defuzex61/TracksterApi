import sqlite3
import os
from pathlib import Path
from typing import List

DB_FILE = "tracks.db"

def init_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tracks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            title TEXT NOT NULL,
            genre TEXT,
            bpm INTEGER,
            key TEXT,
            user_id TEXT NOT NULL,
            cover_path TEXT,
            author TEXT,          
            duration INTEGER,
            play_count INTEGER DEFAULT 0
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS albums (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            user_id TEXT NOT NULL,
            cover_path TEXT,
            play_count INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS album_tracks (
            album_id INTEGER,
            track_id INTEGER,
            FOREIGN KEY (album_id) REFERENCES albums(id),
            FOREIGN KEY (track_id) REFERENCES tracks(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS playlists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            user_id TEXT NOT NULL,
            cover_path TEXT,
            play_count INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS playlist_tracks (
            playlist_id INTEGER,
            track_id INTEGER,
            FOREIGN KEY (playlist_id) REFERENCES playlists(id),
            FOREIGN KEY (track_id) REFERENCES tracks(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS play_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            track_id INTEGER,
            album_id INTEGER,
            playlist_id INTEGER,
            timestamp INTEGER NOT NULL,
            FOREIGN KEY (track_id) REFERENCES tracks(id),
            FOREIGN KEY (album_id) REFERENCES albums(id),
            FOREIGN KEY (playlist_id) REFERENCES playlists(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT,
            email TEXT,
            avatar_path TEXT,
            bio TEXT,
            website TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS followers (
            follower_id TEXT,
            followed_id TEXT,
            PRIMARY KEY (follower_id, followed_id),
            FOREIGN KEY (follower_id) REFERENCES users(user_id),
            FOREIGN KEY (followed_id) REFERENCES users(user_id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS favorites (
            user_id TEXT NOT NULL,
            track_id INTEGER NOT NULL,
            timestamp INTEGER NOT NULL,
            PRIMARY KEY (user_id, track_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (track_id) REFERENCES tracks(id)
        )
    ''')

    conn.commit()
    return conn

conn = init_db()
cursor = conn.cursor()

def save_track(filename: str, title: str, genre: str | None, bpm: int | None, key: str | None, user_id: str, cover_path: str | None, author: str | None, duration: int | None) -> int:
    cursor.execute(
        "INSERT INTO tracks (filename, title, genre, bpm, key, user_id, cover_path, author, duration, play_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)",
        (filename, title, genre, bpm, key, user_id, cover_path, author, duration)
    )
    conn.commit()
    return cursor.lastrowid

def get_track_by_id(track_id: int, user_id: str = None) -> tuple | None:
    if not isinstance(track_id, int):
        raise ValueError(f"track_id must be an integer, got {type(track_id)}: {track_id}")
    query = "SELECT * FROM tracks WHERE id = ?"
    params = (track_id,)
    print(f"Executing query: {query} with params: {params}")
    cursor.execute(query, params)
    return cursor.fetchone()

def increment_track_play_count(track_id: int):
    cursor.execute("UPDATE tracks SET play_count = play_count + 1 WHERE id = ?", (track_id,))
    conn.commit()

def save_album(title: str, user_id: str, cover_path: str | None) -> int:
    cursor.execute("INSERT INTO albums (title, user_id, cover_path, play_count) VALUES (?, ?, ?, 0)", (title, user_id, cover_path))
    conn.commit()
    return cursor.lastrowid

def add_track_to_album(album_id: int, track_id: int):
    cursor.execute("INSERT INTO album_tracks (album_id, track_id) VALUES (?, ?)", (album_id, track_id))
    conn.commit()

def get_album_by_id(album_id: int, user_id: str = None) -> tuple | None:
    cursor.execute("SELECT * FROM albums WHERE id = ?", (album_id,))
    return cursor.fetchone()

def get_album_tracks(album_id: int) -> list:
    cursor.execute("SELECT track_id FROM album_tracks WHERE album_id = ?", (album_id,))
    return [row[0] for row in cursor.fetchall()]

def increment_album_play_count(album_id: int):
    cursor.execute("UPDATE albums SET play_count = play_count + 1 WHERE id = ?", (album_id,))
    conn.commit()

def save_playlist(title: str, user_id: str, cover_path: str | None) -> int:
    cursor.execute("INSERT INTO playlists (title, user_id, cover_path, play_count) VALUES (?, ?, ?, 0)", (title, user_id, cover_path))
    conn.commit()
    return cursor.lastrowid

def add_track_to_playlist(playlist_id: int, track_id: int):
    cursor.execute("INSERT INTO playlist_tracks (playlist_id, track_id) VALUES (?, ?)", (playlist_id, track_id))
    conn.commit()

def get_playlist_by_id(playlist_id: int, user_id: str = None) -> tuple | None:
    cursor.execute("SELECT * FROM playlists WHERE id = ?", (playlist_id,))
    return cursor.fetchone()

def get_playlist_tracks(playlist_id: int) -> list:
    cursor.execute("SELECT track_id FROM playlist_tracks WHERE playlist_id = ?", (playlist_id,))
    return [row[0] for row in cursor.fetchall()]

def increment_playlist_play_count(playlist_id: int):
    cursor.execute("UPDATE playlists SET play_count = play_count + 1 WHERE id = ?", (playlist_id,))
    conn.commit()

def log_play(user_id: str, track_id: int | None = None, album_id: int | None = None, playlist_id: int | None = None):
    import time
    timestamp = int(time.time())
    cursor.execute(
        "INSERT INTO play_history (user_id, track_id, album_id, playlist_id, timestamp) VALUES (?, ?, ?, ?, ?)",
        (user_id, track_id, album_id, playlist_id, timestamp)
    )
    conn.commit()

def get_play_stats(user_id: str, entity_type: str, entity_id: int, start_date: int, end_date: int) -> list:
    column = f"{entity_type}_id"
    cursor.execute(
        f"SELECT DATE(timestamp, 'unixepoch') as play_date, COUNT(*) as play_count "
        f"FROM play_history "
        f"WHERE user_id = ? AND {column} = ? AND timestamp BETWEEN ? AND ? "
        f"GROUP BY play_date "
        f"ORDER BY play_date",
        (user_id, entity_id, start_date, end_date)
    )
    return cursor.fetchall()

def get_tracks_paginated(user_id: str = None, page: int = 1, limit: int = 10) -> tuple[list[tuple], int]:
    cursor.execute("SELECT COUNT(*) FROM tracks")
    total = cursor.fetchone()[0]
    offset = (page - 1) * limit
    
    cursor.execute(
        "SELECT * FROM tracks LIMIT ? OFFSET ?",
        (limit, offset)
    )
    tracks = cursor.fetchall()
    return tracks, total

def follow_user(follower_id: str, followed_id: str) -> bool:
    try:
        cursor.execute(
            "INSERT INTO followers (follower_id, followed_id) VALUES (?, ?)",
            (follower_id, followed_id)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def unfollow_user(follower_id: str, followed_id: str) -> bool:
    cursor.execute(
        "DELETE FROM followers WHERE follower_id = ? AND followed_id = ?",
        (follower_id, followed_id)
    )
    conn.commit()
    return cursor.rowcount > 0

def is_following(follower_id: str, followed_id: str) -> bool:
    cursor.execute(
        "SELECT 1 FROM followers WHERE follower_id = ? AND followed_id = ?",
        (follower_id, followed_id)
    )
    return cursor.fetchone() is not None

def get_username_by_id(user_id: str) -> str:
    cursor.execute("SELECT username FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    return user[0] if user else user_id

def get_user_by_id(user_id: str) -> dict | None:
    cursor.execute(
        "SELECT user_id, username, avatar_path, bio, website FROM users WHERE user_id = ?",
        (user_id,)
    )
    user = cursor.fetchone()
    if not user:
        return None
    return {
        "id": user[0],
        "username": user[1],
        "avatarPath": user[2],
        "bio": user[3],
        "website": user[4],
        "followersCount": 0,
        "tracksCount": 0
    }

def sync_user(user_data: dict):
    user_id = user_data["uid"]
    username = user_data["display_name"]
    email = user_data["email"]
    
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    existing_user = cursor.fetchone()
    
    if existing_user:
        cursor.execute(
            "UPDATE users SET username = ?, email = ? WHERE user_id = ?",
            (username, email, user_id)
        )
    else:
        cursor.execute(
            "INSERT INTO users (user_id, username, email) VALUES (?, ?, ?)",
            (user_id, username, email)
        )
    
    conn.commit()

def search_tracks(query: str = "", user_id: str = "", page: int = 1, limit: int = 20) -> dict:
    query_params = []
    count_params = []
    base_query = "SELECT * FROM tracks"
    count_query = "SELECT COUNT(*) FROM tracks"
    conditions = []
    
    if query:
        conditions.append("title LIKE ?")
        query_params.append(f"%{query}%")
        count_params.append(f"%{query}%")
    
    if user_id:
        conditions.append("user_id = ?")
        query_params.append(user_id)
        count_params.append(user_id)
    
    if conditions:
        condition_str = " WHERE " + " AND ".join(conditions)
        base_query += condition_str
        count_query += condition_str
    
    offset = (page - 1) * limit
    base_query += " LIMIT ? OFFSET ?"
    query_params.extend([limit, offset])
    
    try:
        cursor.execute(count_query, count_params)
        total = cursor.fetchone()[0]
        
        cursor.execute(base_query, query_params)
        tracks = cursor.fetchall()
        
        tracks_list = []
        for track in tracks:
            bpm = track[4]
            try:
                bpm = int(bpm) if bpm is not None else None
            except (ValueError, TypeError):
                print(f"Invalid bpm value for track {track[0]}: {bpm}. Setting to None.")
                bpm = None
            
            author = track[8]
            author = author if author is not None else "Unknown"
            
            track_dict = {
                "id": track[0],
                "filename": track[1],
                "title": track[2],
                "genre": track[3],
                "bpm": bpm,
                "key": track[5],
                "user_id": track[6],
                "cover_path": track[7],
                "author": author,
                "duration": track[9],
                "play_count": track[10]
            }
            tracks_list.append(track_dict)
        
        print(f"Found tracks: {tracks_list}")
        
        total_pages = (total + limit - 1) // limit
        
        return {
            "tracks": tracks_list,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages
        }
    except Exception as e:
        print(f"Error searching tracks: {str(e)}")
        return {
            "tracks": [],
            "total": 0,
            "page": page,
            "limit": limit,
            "total_pages": 0
        }

def search_albums(query: str = "", user_id: str = "", page: int = 1, limit: int = 20) -> dict:
    query_params = []
    count_params = []
    base_query = "SELECT * FROM albums"
    count_query = "SELECT COUNT(*) FROM albums"
    conditions = []
    
    if query:
        conditions.append("title LIKE ?")
        query_params.append(f"%{query}%")
        count_params.append(f"%{query}%")
    
    if user_id:
        conditions.append("user_id = ?")
        query_params.append(user_id)
        count_params.append(user_id)
    
    if conditions:
        condition_str = " WHERE " + " AND ".join(conditions)
        base_query += condition_str
        count_query += condition_str
    
    offset = (page - 1) * limit
    base_query += " LIMIT ? OFFSET ?"
    query_params.extend([limit, offset])
    
    try:
        cursor.execute(count_query, count_params)
        total = cursor.fetchone()[0]
        
        cursor.execute(base_query, query_params)
        albums = cursor.fetchall()
        
        albums_list = []
        for album in albums:
            album_id = album[0]
            # Получаем треки альбома
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
            
            album_dict = {
                "id": album[0],
                "title": album[1],
                "cover_path": album[3],
                "play_count": album[4],
                "tracks": tracks_response
            }
            albums_list.append(album_dict)
        
        print(f"Found albums: {albums_list}")
        
        total_pages = (total + limit - 1) // limit
        
        return {
            "albums": albums_list,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages
        }
    except Exception as e:
        print(f"Error searching albums: {str(e)}")
        return {
            "albums": [],
            "total": 0,
            "page": page,
            "limit": limit,
            "total_pages": 0
        }

def fetch_most_played_tracks(page: int, limit: int) -> tuple[list[tuple], int]:
    cursor.execute("SELECT COUNT(*) FROM tracks")
    total = cursor.fetchone()[0]
    offset = (page - 1) * limit
    cursor.execute(
        "SELECT * FROM tracks ORDER BY play_count DESC LIMIT ? OFFSET ?",
        (limit, offset)
    )
    tracks = cursor.fetchall()
    return tracks, total

def update_track_cover(track_id: int, cover_path: str, user_id: str) -> dict:
    track = get_track_by_id(track_id)
    if not track:
        raise ValueError("Track not found")
    if track[6] != user_id:
        raise ValueError("Not authorized to update this track")

    cursor.execute("UPDATE tracks SET cover_path = ? WHERE id = ?", (cover_path, track_id))
    conn.commit()

    updated_track = get_track_by_id(track_id)
    return {
        "id": updated_track[0],
        "filename": updated_track[1],
        "title": updated_track[2],
        "genre": updated_track[3],
        "bpm": updated_track[4],
        "key": updated_track[5],
        "user_id": updated_track[6],
        "cover_path": updated_track[7],
        "author": updated_track[8],
        "duration": updated_track[9],
        "play_count": updated_track[10]
    }

def upload_album(title: str, user_id: str, cover_path: str | None, tracks_data: list[dict] | None) -> dict:
    try:
        album_id = save_album(title=title, user_id=user_id, cover_path=cover_path)

        if tracks_data:
            track_ids = []
            for track_data in tracks_data:
                filename = track_data.get("filename")
                title = track_data.get("title")
                genre = track_data.get("genre")
                bpm = track_data.get("bpm")
                key = track_data.get("key")
                author = track_data.get("author")
                duration = track_data.get("duration")

                if not all([filename, title, user_id]):
                    print(f"Missing required fields for track: {track_data}")
                    continue

                track_id = save_track(
                    filename=filename,
                    title=title,
                    genre=genre,
                    bpm=bpm,
                    key=key,
                    user_id=user_id,
                    cover_path=cover_path, 
                    author=author,
                    duration=duration
                )
                track_ids.append(track_id)
                add_track_to_album(album_id=album_id, track_id=track_id)

        album = get_album_by_id(album_id, user_id)
        if not album:
            raise ValueError(f"Failed to retrieve album with ID {album_id}")

        return {
            "id": album[0],
            "title": album[1],
            "user_id": album[2],
            "cover_path": album[3],
            "play_count": album[4]
        }
    except Exception as e:
        print(f"Error uploading album: {str(e)}")
        raise

def get_user_albums(user_id: str = None) -> List[dict]:

    if user_id:
        cursor.execute("SELECT id, title, user_id, cover_path, play_count FROM albums WHERE user_id = ?", (user_id,))
    else:
        cursor.execute("SELECT id, title, user_id, cover_path, play_count FROM albums")
    
    albums = cursor.fetchall()
    
    result = []
    for album in albums:
        album_id = album[0]
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
        
        album_response = {
            "id": album[0],
            "title": album[1],
            "cover_path": album[3],
            "play_count": album[4],
            "tracks": tracks_response
        }
        result.append(album_response)
    
    return result

def add_track_to_favorites(user_id: str, track_id: int) -> bool:
    import time
    timestamp = int(time.time())
    try:
        cursor.execute(
            "INSERT INTO favorites (user_id, track_id, timestamp) VALUES (?, ?, ?)",
            (user_id, track_id, timestamp)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def remove_track_from_favorites(user_id: str, track_id: int) -> bool:
    cursor.execute(
        "DELETE FROM favorites WHERE user_id = ? AND track_id = ?",
        (user_id, track_id)
    )
    conn.commit()
    return cursor.rowcount > 0

def get_user_favorites(user_id: str, page: int = 1, limit: int = 20) -> tuple[list[tuple], int]:
    cursor.execute("SELECT COUNT(*) FROM favorites WHERE user_id = ?", (user_id,))
    total = cursor.fetchone()[0]
    
    offset = (page - 1) * limit
    cursor.execute(
        """
        SELECT t.* FROM tracks t
        JOIN favorites f ON t.id = f.track_id
        WHERE f.user_id = ?
        ORDER BY f.timestamp DESC
        LIMIT ? OFFSET ?
        """,
        (user_id, limit, offset)
    )
    tracks = cursor.fetchall()
    return tracks, total

def is_track_in_favorites(user_id: str, track_id: int) -> bool:
    cursor.execute(
        "SELECT 1 FROM favorites WHERE user_id = ? AND track_id = ?",
        (user_id, track_id)
    )
    return cursor.fetchone() is not None   

def get_user_by_id(user_id: str) -> dict | None:
    cursor.execute(
        "SELECT user_id, username, avatar_path, bio, website FROM users WHERE user_id = ?",
        (user_id,)
    )
    user = cursor.fetchone()
    if not user:
        return None
    return {
        "id": user[0],
        "username": user[1],
        "avatarPath": user[2],
        "bio": user[3],
        "website": user[4],
        "followersCount": 0,
        "tracksCount": 0
    }

def get_user_by_username(username: str) -> dict | None:
    cursor.execute(
        "SELECT user_id, username, avatar_path, bio, website FROM users WHERE username = ?",
        (username,)
    )
    user = cursor.fetchone()
    if not user:
        return None
    return {
        "id": user[0],
        "username": user[1],
        "avatarPath": user[2],
        "bio": user[3],
        "website": user[4],
        "followersCount": 0,
        "tracksCount": 0
    }
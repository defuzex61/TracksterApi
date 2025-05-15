from fastapi import APIRouter, Depends, HTTPException
from firebase_admin import auth

from src.auth.firebase_auth import get_current_user
from src.db.database import follow_user, get_user_by_id, get_user_by_username, is_following, search_albums, search_tracks, sync_user, unfollow_user
from src.models.track import PaginatedTracksResponse
from src.models.trackster_user import TracksterSearchResponse, TracksterUser
from src.models.album import PaginatedAlbumsResponse

router = APIRouter()

# Эндпоинт для получения профиля пользователя
@router.get("/users/{user_id}", response_model=TracksterUser)
async def get_user(user_id: str, current_user: dict = Depends(get_current_user)):
    try:
        print(f"Пытаемся найти пользователя в Firebase с UID: {user_id}")
        firebase_user = auth.get_user(user_id)
        print(f"Найден пользователь: {firebase_user.uid}, username: {firebase_user.display_name}")
        username = firebase_user.display_name if firebase_user.display_name else user_id
        email = firebase_user.email
    except Exception as e:
        print(f"Ошибка Firebase: {str(e)}")
        raise HTTPException(status_code=404, detail="User not found in Firebase")

    sync_user({
        "uid": user_id,
        "display_name": username,
        "email": email
    })
    
    user_dict = get_user_by_id(user_id)
    if not user_dict:
        raise HTTPException(status_code=404, detail="User not found in database")
    
    # Проверяем и нормализуем ключи
    if 'id' in user_dict:
        user_dict['user_id'] = user_dict.pop('id')  # Переименовываем 'id' в 'user_id'
    else:
        user_dict['user_id'] = user_id  # Используем user_id из запроса, если 'id' нет
    
    # Добавляем отсутствующие поля с значениями по умолчанию
    if 'followers_count' not in user_dict:
        user_dict['followers_count'] = 0
    if 'tracks_count' not in user_dict:
        user_dict['tracks_count'] = 0
    
    # Добавляем email из Firebase
    user_dict['email'] = email
    
    # Отладочный вывод для проверки
    print(f"Возвращаемый user_dict: {user_dict}")
    return TracksterUser(**user_dict)

# Эндпоинт для поиска треков
@router.get("/search-tracks", response_model=PaginatedTracksResponse)
async def search_tracks_endpoint(
    query: str = "",
    user_id: str = "",
    page: int = 1,
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    return search_tracks(query=query, user_id=user_id, page=page, limit=limit)

# Эндпоинт для поиска альбомов
@router.get("/search-albums", response_model=PaginatedAlbumsResponse)
async def search_albums_endpoint(
    query: str = "",
    user_id: str = "",
    page: int = 1,
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    return search_albums(query=query, user_id=user_id, page=page, limit=limit)

# Универсальный эндпоинт для поиска (и треки, и альбомы)
@router.get("/search", response_model=TracksterSearchResponse)
async def unified_search_endpoint(
    query: str = "",
    user_id: str = "",
    page: int = 1,
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    # Ищем треки
    tracks_result = search_tracks(query=query, user_id=user_id, page=page, limit=limit)
    
    # Ищем альбомы
    albums_result = search_albums(query=query, user_id=user_id, page=page, limit=limit)
    
    # Объединяем результаты
    return {
        "tracks": tracks_result["tracks"],
        "albums": albums_result["albums"],
        "total_tracks": tracks_result["total"],
        "total_albums": albums_result["total"], 
        "page": page,
        "limit": limit,
        "total_pages_tracks": tracks_result["total_pages"],
        "total_pages_albums": albums_result["total_pages"]
    }

# Эндпоинты для управления подписками
@router.post("/users/{user_id}/follow")
async def follow(user_id: str, current_user: dict = Depends(get_current_user)):
    follower_id = current_user["uid"]
    if follower_id == user_id:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")
    
    success = follow_user(follower_id, user_id)
    if not success:
        raise HTTPException(status_code=400, detail="Already following")
    
    return {"success": True}

@router.post("/users/{user_id}/unfollow")
async def unfollow(user_id: str, current_user: dict = Depends(get_current_user)):
    follower_id = current_user["uid"]
    success = unfollow_user(follower_id, user_id)
    if not success:
        raise HTTPException(status_code=400, detail="Not following this user")
    
    return {"success": True}

@router.get("/users/{user_id}/is_following")
async def check_following(user_id: str, current_user: dict = Depends(get_current_user)):
    follower_id = current_user["uid"]
    following = is_following(follower_id, user_id)
    return {"is_following": following}

@router.get("/users/by-username/{username}", response_model=TracksterUser)
async def get_user_by_username_endpoint(username: str, current_user: dict = Depends(get_current_user)):
    user_dict = get_user_by_username(username)
    if not user_dict:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Нормализуем ключи, если нужно
    if 'id' in user_dict:
        user_dict['user_id'] = user_dict.pop('id')
    
    # Получаем дополнительную информацию из Firebase, если возможно
    try:
        firebase_user = auth.get_user_by_email(user_dict.get('email', ''))
        if firebase_user and firebase_user.email:
            user_dict['email'] = firebase_user.email
    except Exception:
        # Если ошибка при получении данных из Firebase, используем только данные из БД
        pass
    
    return TracksterUser(**user_dict)
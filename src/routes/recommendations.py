from fastapi import APIRouter, Depends, HTTPException
from src.services.recommendation_service import RecommendationService
from src.auth.firebase_auth import get_current_user
from typing import List, Dict

router = APIRouter()
recommendation_service = RecommendationService()

@router.get("/recommendations", response_model=List[Dict])
async def get_recommendations(limit: int = 10, user: dict = Depends(get_current_user)):

    try:
        user_id = user["uid"]
        recommendations = recommendation_service.get_recommendations(user_id, num_recommendations=limit)
        return recommendations
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate recommendations: {str(e)}")

@router.post("/recommendations/reset")
async def reset_recommendation_model(user: dict = Depends(get_current_user)):

    try:
        result = recommendation_service.reset_model()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset recommendation model: {str(e)}")

@router.get("/recommendations/genre-analysis")
async def analyze_genre_recommendations(user: dict = Depends(get_current_user)):
    try:
        user_id = user["uid"]
        
        # Убедимся, что модель обучена
        if not recommendation_service.is_trained:
            recommendation_service.train_model()
            
        # Получим историю прослушиваний
        play_history = recommendation_service._get_play_history()
        user_history = [item for item in play_history if item["user_id"] == user_id]
        
        # Получим информацию о треках
        tracks = recommendation_service._get_all_tracks()
        track_map = {track["id"]: track for track in tracks}
        
        # Анализируем жанры в истории прослушиваний
        user_genres = {}
        for play in user_history:
            track_id = play["track_id"]
            if track_id in track_map:
                genre = track_map[track_id].get("genre", "Unknown")
                if genre:
                    user_genres[genre] = user_genres.get(genre, 0) + play["play_count"]
        
        # Получаем рекомендации
        recommendations = recommendation_service.get_recommendations(user_id, num_recommendations=10)
        
        # Анализируем жанры в рекомендациях
        recommendation_genres = {}
        for track in recommendations:
            genre = track.get("genre", "Unknown")
            if genre:
                recommendation_genres[genre] = recommendation_genres.get(genre, 0) + 1
        
        # Категории жанров и матрица сходства
        genre_categories = recommendation_service.recommender.genre_categories
        category_similarity = recommendation_service.recommender.category_similarity
        
        # Сформируем итоговый отчет
        return {
            "user_id": user_id,
            "play_history_count": len(user_history),
            "user_genre_preferences": user_genres,
            "recommendation_genre_distribution": recommendation_genres,
            "genre_categories": genre_categories,
            "genres_considered_similar": [
                {"genres": [g1, g2], "similarity": similarity}
                for g1, sims in category_similarity.items()
                for g2, similarity in sims.items()
                if similarity >= 0.7 and g1 != g2
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze genre recommendations: {str(e)}")
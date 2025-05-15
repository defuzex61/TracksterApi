from src.recommenders.lightfm_recommender import LightFMRecommender
from src.db.database import get_tracks_paginated, get_track_by_id, get_play_stats, search_tracks, get_user_albums
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class RecommendationService:
    def __init__(self):
        self.recommender = LightFMRecommender()
        self.is_trained = False

    def reset_model(self):
        """Сброс состояния модели, чтобы она переобучилась при следующем запросе."""
        logger.info("Resetting recommendation model.")
        self.is_trained = False
        self.recommender = LightFMRecommender()
        return {"status": "success", "message": "Recommendation model has been reset successfully."}

    def train_model(self):
        """Обучение модели на основе данных из базы."""
        # Получаем историю прослушиваний
        play_history = self._get_play_history()
        logger.info(f"Retrieved {len(play_history)} play history records for training")

        # Получаем все треки
        tracks = self._get_all_tracks()
        logger.info(f"Retrieved {len(tracks)} tracks for training")

        # Анализ жанров
        genre_distribution = self._analyze_genres(tracks)
        logger.info(f"Genre distribution in dataset: {genre_distribution}")

        # Обучаем модель
        self.recommender.train(play_history, tracks, epochs=40)
        self.is_trained = True
        logger.info("Recommendation model trained successfully.")

    def _analyze_genres(self, tracks: List[Dict]) -> Dict[str, int]:
        """Анализирует распределение жанров в датасете."""
        genres = {}
        for track in tracks:
            genre = track.get('genre', 'Unknown')
            if not genre:
                genre = 'Unknown'
            
            # Разделяем составные жанры
            import re
            genre_parts = re.split(r'[/,&]', genre)
            for part in genre_parts:
                part = part.strip()
                if part:
                    genres[part] = genres.get(part, 0) + 1
        
        # Сортируем по популярности
        return dict(sorted(genres.items(), key=lambda x: x[1], reverse=True))

    def _get_play_history(self) -> List[Dict]:
        """Извлечение истории прослушиваний из базы данных."""
        from src.db.database import conn
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, track_id, COUNT(*) as play_count FROM play_history WHERE track_id IS NOT NULL GROUP BY user_id, track_id")
        play_history = [
            {"user_id": row[0], "track_id": row[1], "play_count": row[2]}
            for row in cursor.fetchall()
        ]
        return play_history

    def _get_all_tracks(self) -> List[Dict]:
        """Извлечение всех треков из базы данных."""
        from src.db.database import conn
        cursor = conn.cursor()
        cursor.execute("SELECT id, genre, bpm, key, author FROM tracks")
        tracks = [
            {"id": row[0], "genre": row[1], "bpm": row[2], "key": row[3], "author": row[4]}
            for row in cursor.fetchall()
        ]
        return tracks

    def get_recommendations(self, user_id: str, num_recommendations: int = 10) -> List[Dict]:
        """Получение рекомендаций для пользователя с улучшенным учетом жанровой близости."""
        try:
            if not self.is_trained:
                logger.warning("Model is not trained, training now...")
                self.train_model()

            # Получаем рекомендованные track_id
            logger.info(f"Getting recommendations for user {user_id}, limit={num_recommendations}")
            recommended_track_ids = self.recommender.recommend(user_id, num_recommendations)
            logger.info(f"Received {len(recommended_track_ids)} recommended track IDs: {recommended_track_ids}")

            # Извлекаем информацию о треках
            recommended_tracks = []
            
            # Анализируем жанры рекомендованных треков
            recommendation_genres = {}
            
            for track_id in recommended_track_ids:
                try:
                    # Преобразуем track_id в целое число
                    track_id_int = int(track_id)
                    logger.info(f"Getting details for track ID {track_id_int} (original: {track_id})")
                    track = get_track_by_id(track_id_int)
                    if track:
                        # Сохраняем жанр для анализа
                        genre = track[3] if track[3] else "Unknown"
                        recommendation_genres[genre] = recommendation_genres.get(genre, 0) + 1
                        
                        logger.info(f"Track found: {track[0]}, {track[2]}, genre: {genre}")
                        track_dict = {
                            "id": track[0],
                            "filename": track[1],
                            "title": track[2],
                            "genre": track[3],
                            "bpm": track[4],
                            "key": track[5],
                            "user_id": track[6],
                            "cover_path": track[7],
                            "author": track[8],
                            "duration": track[9],
                            "play_count": track[10]
                        }
                        recommended_tracks.append(track_dict)
                    else:
                        logger.warning(f"Track with ID {track_id_int} not found")
                except (ValueError, TypeError) as e:
                    logger.error(f"Error converting track_id '{track_id}' to integer: {e}")
                    continue

            # Логируем распределение жанров в рекомендациях
            logger.info(f"Genre distribution in recommendations: {recommendation_genres}")
            logger.info(f"Returning {len(recommended_tracks)} recommended tracks")
            return recommended_tracks
        except Exception as e:
            logger.error(f"Error in get_recommendations: {e}", exc_info=True)
            raise
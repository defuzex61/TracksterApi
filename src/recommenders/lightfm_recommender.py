import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix, hstack
from lightfm import LightFM
from typing import List, Dict, Tuple
import logging
import re

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LightFMRecommender:
    def __init__(self):
        self.model = None
        self.user_id_map = {}
        self.track_id_map = {}
        self.interaction_matrix = None
        self.item_features = None
        self.num_users = 0
        self.num_items = 0
        self.genre_similarity = {}
        
        # Определение близости жанров
        self._init_genre_similarity()
        
    def _init_genre_similarity(self):

        self.genre_categories = {
            "hip_hop": ["rap", "hip hop", "trap", "gangsta rap", "boom bap", "conscious rap"],
            "cloud_rap": ["cloud rap", "phonk", "vaporwave", "witch house"],
            "electronic": ["electronic", "techno", "house", "trance", "drum and bass", "dubstep"],
            "ambient": ["ambient", "chillout", "downtempo", "atmospheric"],
            "idm": ["idm", "glitch", "breakcore", "experimental electronic"],
            "rock": ["rock", "indie", "alternative", "metal", "punk", "post-rock", "grunge"],
            "pop": ["pop", "synth pop", "dance", "disco", "kpop", "jpop"],
            "jazz": ["jazz", "blues", "soul", "funk", "fusion"],
            "classical": ["classical", "orchestra", "instrumental", "chamber", "opera"],
            "folk": ["folk", "acoustic", "singer-songwriter", "country"],
            "screamo": ["screamo", "emo", "post-hardcore", "metalcore"]
        }
        
        # Строим обратное сопоставление
        genre_to_category = {}
        for category, genres in self.genre_categories.items():
            for genre in genres:
                genre_to_category[genre] = category
        
        self.genre_to_category = genre_to_category
        

        self.category_similarity = {
            "hip_hop": {"hip_hop": 1.0, "cloud_rap": 0.8, "electronic": 0.4, "ambient": 0.3, "idm": 0.2, 
                      "rock": 0.3, "pop": 0.5, "jazz": 0.6, "classical": 0.1, "folk": 0.3, "screamo": 0.2},
            
            "cloud_rap": {"hip_hop": 0.8, "cloud_rap": 1.0, "electronic": 0.5, "ambient": 0.6, "idm": 0.4, 
                        "rock": 0.2, "pop": 0.4, "jazz": 0.3, "classical": 0.1, "folk": 0.2, "screamo": 0.5},
            
            "electronic": {"hip_hop": 0.4, "cloud_rap": 0.5, "electronic": 1.0, "ambient": 0.7, "idm": 0.8, 
                         "rock": 0.4, "pop": 0.7, "jazz": 0.4, "classical": 0.3, "folk": 0.2, "screamo": 0.2},
            
            "ambient": {"hip_hop": 0.3, "cloud_rap": 0.6, "electronic": 0.7, "ambient": 1.0, "idm": 0.7, 
                      "rock": 0.3, "pop": 0.3, "jazz": 0.5, "classical": 0.6, "folk": 0.5, "screamo": 0.1},
            
            "idm": {"hip_hop": 0.2, "cloud_rap": 0.4, "electronic": 0.8, "ambient": 0.7, "idm": 1.0, 
                  "rock": 0.3, "pop": 0.4, "jazz": 0.3, "classical": 0.5, "folk": 0.2, "screamo": 0.2},
            
            "rock": {"hip_hop": 0.3, "cloud_rap": 0.2, "electronic": 0.4, "ambient": 0.3, "idm": 0.1, 
                   "rock": 1.0, "pop": 0.6, "jazz": 0.4, "classical": 0.3, "folk": 0.6, "screamo": 0.7},
            
            "pop": {"hip_hop": 0.5, "cloud_rap": 0.4, "electronic": 0.7, "ambient": 0.3, "idm": 0.4, 
                  "rock": 0.6, "pop": 1.0, "jazz": 0.5, "classical": 0.3, "folk": 0.5, "screamo": 0.3},
            
            "jazz": {"hip_hop": 0.6, "cloud_rap": 0.3, "electronic": 0.4, "ambient": 0.5, "idm": 0.3, 
                   "rock": 0.4, "pop": 0.5, "jazz": 1.0, "classical": 0.6, "folk": 0.6, "screamo": 0.1},
            
            "classical": {"hip_hop": 0.1, "cloud_rap": 0.1, "electronic": 0.3, "ambient": 0.6, "idm": 0.5, 
                        "rock": 0.3, "pop": 0.3, "jazz": 0.6, "classical": 1.0, "folk": 0.5, "screamo": 0.1},
            
            "folk": {"hip_hop": 0.3, "cloud_rap": 0.2, "electronic": 0.2, "ambient": 0.5, "idm": 0.2, 
                   "rock": 0.6, "pop": 0.5, "jazz": 0.6, "classical": 0.5, "folk": 1.0, "screamo": 0.2},
            
            "screamo": {"hip_hop": 0.2, "cloud_rap": 0.5, "electronic": 0.2, "ambient": 0.1, "idm": 0.2, 
                      "rock": 0.7, "pop": 0.3, "jazz": 0.1, "classical": 0.1, "folk": 0.2, "screamo": 1.0}
        }
        
        # Создаем словарь для нормализованного поиска жанров
        self.normalized_genres = {}
        for cat, genres in self.genre_categories.items():
            for genre in genres:
                self.normalized_genres[self._normalize_genre(genre)] = genre
        
    def _normalize_genre(self, genre: str) -> str:
        if not genre:
            return ""
        return genre.lower().strip().replace('-', ' ')
        
    def _get_genre_category(self, genre: str) -> str:
        if not genre:
            return "unknown"
            
        genres_found = []
        
        # Нормализуем входной жанр
        genre_lower = self._normalize_genre(genre)
        
        # Разбиваем составные жанры
        genre_parts = re.split(r'[/,&]', genre_lower)
        for part in genre_parts:
            part = part.strip()
            if not part:
                continue
                
            # Прямое совпадение
            normalized_part = self._normalize_genre(part)
            if normalized_part in self.normalized_genres:
                matched_genre = self.normalized_genres[normalized_part]
                genres_found.append(self.genre_to_category.get(matched_genre, "unknown"))
                continue
                
            # Частичное совпадение 
            for known_genre, category in self.genre_to_category.items():
                if known_genre in normalized_part or normalized_part in known_genre:
                    genres_found.append(category)
                    break
        
        # Если нашли хотя бы один жанр, возвращаем его, иначе unknown
        return genres_found[0] if genres_found else "unknown"
    
    def _calculate_genre_distance(self, genre1: str, genre2: str) -> float:
        if not genre1 or not genre2:
            return 0.0
            
        cat1 = self._get_genre_category(genre1)
        cat2 = self._get_genre_category(genre2)
        
        # Если оба жанра неизвестны или одинаковы
        if cat1 == "unknown" and cat2 == "unknown":
            return 0.5  # Средняя близость
        elif cat1 == cat2:
            return 1.0  # Максимальная близость
            
        # Используем матрицу сходства категорий
        if cat1 in self.category_similarity and cat2 in self.category_similarity[cat1]:
            return self.category_similarity[cat1][cat2]
        
        return 0.2  # Значение по умолчанию для неизвестных соотношений

    def _prepare_interactions(self, play_history: List[dict]) -> coo_matrix:
        """Подготовка матрицы взаимодействий (пользователь-трек)."""
        # Преобразуем историю прослушиваний в DataFrame
        df = pd.DataFrame(play_history)
        if df.empty:
            logger.warning("Play history is empty.")
            return None

        # Убедимся, что track_id - целые числа 
        track_ids_valid = []
        for tid in df['track_id'].unique():
            try:
                # Сохраняем исходные значения в track_id_map
                track_ids_valid.append(tid)
            except (ValueError, TypeError):
                logger.warning(f"Invalid track_id: {tid}, skipping")

        # Создаём отображения user_id и track_id в индексы
        user_ids = df['user_id'].unique()
        track_ids = np.array(track_ids_valid)
        
        logger.info(f"Unique user_ids: {user_ids}")
        logger.info(f"Unique track_ids: {track_ids}")

        self.user_id_map = {uid: idx for idx, uid in enumerate(user_ids)}
        self.track_id_map = {tid: idx for idx, tid in enumerate(track_ids)}

        self.num_users = len(user_ids)
        self.num_items = len(track_ids)

        logger.info(f"User ID map: {self.user_id_map}")
        logger.info(f"Track ID map: {self.track_id_map}")

        # Создаём матрицу взаимодействий
        rows = []
        cols = []
        weights = []
        
        for _, row in df.iterrows():
            user_id = row['user_id']
            track_id = row['track_id']
            
            if user_id in self.user_id_map and track_id in self.track_id_map:
                rows.append(self.user_id_map[user_id])
                cols.append(self.track_id_map[track_id])
                weights.append(float(row['play_count']))
        
        if not rows:
            logger.warning("No valid interactions found after filtering.")
            return coo_matrix((self.num_users, self.num_items))

        interaction_matrix = coo_matrix(
            (weights, (rows, cols)),
            shape=(self.num_users, self.num_items)
        )
        logger.info(f"Interaction matrix shape: {interaction_matrix.shape}")
        return interaction_matrix

    def _prepare_item_features(self, tracks: List[dict]) -> coo_matrix:
        """Подготовка признаков треков (жанр, BPM, тональность)."""
        if not tracks:
            logger.warning("Tracks list is empty.")
            return None

        # Фильтруем треки, чтобы включить только те, что есть в track_id_map
        valid_tracks = []
        track_indices = []
        for track in tracks:
            track_id = track['id']
            if track_id in self.track_id_map:
                valid_tracks.append(track)
                track_indices.append(self.track_id_map[track_id])
            else:
                logger.warning(f"Track ID {track_id} not found in track_id_map, skipping")
                
        if not valid_tracks:
            logger.warning("No valid tracks found after filtering.")
            # Создаем пустую матрицу признаков
            return coo_matrix((self.num_items, 1))
            
        logger.info(f"Processing {len(valid_tracks)} valid tracks for features")
        
        df = pd.DataFrame(valid_tracks)

        # Обрабатываем жанры (one-hot encoding с усиленным весом)
        genres = set()
        track_genre_categories = []
        
        # Собираем все уникальные жанры и категории
        for track in valid_tracks:
            genre = track.get('genre', 'Unknown')
            if pd.isna(genre):
                genre = 'Unknown'
            
            # Парсим комбинированные жанры
            if genre and isinstance(genre, str):
                # Разделяем такие жанры как "Cloud Rap/Screamo" на отдельные жанры
                genre_parts = re.split(r'[/,&]', genre)
                for part in genre_parts:
                    part = part.strip()
                    if part:
                        genres.add(part)
                        
                # Сохраняем оригинальный жанр трека
                track_genre_categories.append(self._get_genre_category(genre))
            else:
                track_genre_categories.append("unknown")
        
        genres = list(genres)
        genre_map = {genre: idx for idx, genre in enumerate(genres)}
        
        # Создаем матрицу жанров с усиленным весом (вес 3.0) - повышаем важность жанров
        genre_matrix = np.zeros((len(valid_tracks), len(genres)))

        for idx, track in enumerate(valid_tracks):
            genre = track.get('genre')
            if genre and isinstance(genre, str):
                # Разделяем составные жанры
                genre_parts = re.split(r'[/,&]', genre)
                for part in genre_parts:
                    part = part.strip()
                    if part and part in genre_map:
                        # Увеличиваем вес жанра для лучшего учета
                        genre_matrix[idx, genre_map[part]] = 3.0
        
        # Добавляем категориальную матрицу жанров
        categories = list(set(self.genre_categories.keys())) + ["unknown"]
        category_map = {cat: idx for idx, cat in enumerate(categories)}
        
        category_matrix = np.zeros((len(valid_tracks), len(categories)))
        for idx, category in enumerate(track_genre_categories):
            if category in category_map:
                # Повышаем вес категории жанра до 2.0
                category_matrix[idx, category_map[category]] = 2.0

        # Обрабатываем BPM (нормализуем)
        bpm_values = []
        for track in valid_tracks:
            try:
                bpm = float(track.get('bpm', 120) or 120)
                bpm_values.append(bpm)
            except (ValueError, TypeError):
                bpm_values.append(120.0)  # Значение по умолчанию
                
        bpm_array = np.array(bpm_values)
        bpm_max = float(np.max(bpm_array)) if bpm_array.size > 0 and np.max(bpm_array) > 0 else 1.0
        bpm_normalized = bpm_array / bpm_max

        # Обрабатываем тональность (числовой код)
        keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        key_map = {key: idx for idx, key in enumerate(keys)}
        
        key_values = []
        for track in valid_tracks:
            key = track.get('key')
            if key and isinstance(key, str):
                # Извлекаем базовую ноту (C, D, E, и т.д.)
                base_key = key[0] if len(key) > 0 else 'C'
                if len(key) > 1 and key[1] == '#':
                    base_key += '#'
                    
                if base_key in key_map:
                    key_values.append(float(key_map[base_key]))
                else:
                    key_values.append(float(key_map['C']))  # По умолчанию
            else:
                key_values.append(float(key_map['C']))  # По умолчанию

        # Объединяем признаки
        feature_matrix = np.hstack([
            genre_matrix,            # Жанровые признаки (вес 3.0)
            category_matrix,         # Категории жанров (вес 2.0)
            bpm_normalized.reshape(-1, 1) * 0.8,  # BPM с пониженным весом
            np.array(key_values).reshape(-1, 1) * 0.5  # Тональность с пониженным весом
        ])

        # Создаем финальную матрицу признаков с правильным размером (num_items x feature_size)
        full_feature_matrix = np.zeros((self.num_items, feature_matrix.shape[1]))
        for idx, track_idx in enumerate(track_indices):
            full_feature_matrix[track_idx] = feature_matrix[idx]

        item_features = coo_matrix(full_feature_matrix)
        logger.info(f"Item features shape: {item_features.shape}")
        return item_features

    def train(self, play_history: List[dict], tracks: List[dict], epochs: int = 30):
        """Обучение модели LightFM."""
        try:
            self.interaction_matrix = self._prepare_interactions(play_history)
            self.item_features = self._prepare_item_features(tracks)

            if self.interaction_matrix is None or self.item_features is None:
                logger.error("Cannot train model: interaction matrix or item features are missing.")
                return

            if self.interaction_matrix.shape[0] == 0 or self.interaction_matrix.shape[1] == 0:
                logger.error("Cannot train model: interaction matrix has zero dimension.")
                return
                
            if self.item_features.shape[0] == 0:
                logger.error("Cannot train model: item features matrix has zero rows.")
                return

            # Инициализация модели с улучшенными параметрами
            self.model = LightFM(
                no_components=50,     # Увеличиваем размер скрытых векторов для лучших рекомендаций
                loss='warp',          # Loss-функция для рекомендаций
                learning_rate=0.02,   # Уменьшаем скорость обучения для лучшей сходимости
                item_alpha=1e-5,      # Регуляризация признаков элементов
                user_alpha=1e-5,      # Регуляризация признаков пользователей
                max_sampled=25,       # Увеличиваем количество негативных примеров
                random_state=42
            )

            # Обучение
            logger.info("Training LightFM model...")
            logger.info(f"Interaction matrix shape for training: {self.interaction_matrix.shape}")
            logger.info(f"Item features shape for training: {self.item_features.shape}")
            
            self.model.fit(
                interactions=self.interaction_matrix,
                item_features=self.item_features,
                epochs=epochs,
                num_threads=4,
                verbose=True
            )
            logger.info("Model training completed.")
            
            # Сохраняем жанры треков для быстрого доступа
            self.track_genres = {}
            self._prepare_track_genres(tracks)
            
        except Exception as e:
            logger.error(f"Error training LightFM model: {str(e)}")
            self.model = None  # Сбросим модель при ошибке
            raise
            
    def _prepare_track_genres(self, tracks: List[dict]):
        """Подготавливает словарь жанров треков для быстрого доступа."""
        for track in tracks:
            if track['id'] in self.track_id_map:
                genre = track.get('genre', 'Unknown')
                if not genre or pd.isna(genre):
                    genre = 'Unknown'
                self.track_genres[self.track_id_map[track['id']]] = genre

    def get_similar_genre_items(self, user_id: str, item_idx: int, n: int = 5) -> List[int]:
        """Получает треки с похожими жанрами, используя матрицу сходства жанров."""
        if item_idx >= self.num_items:
            return []
            
        # Проверяем наличие пользователя
        if user_id not in self.user_id_map:
            return []
            
        user_idx = self.user_id_map[user_id]
        
        # Получаем жанр трека
        base_genre = self.track_genres.get(item_idx, 'Unknown')
        
        # Вычисляем сходство жанров для всех треков
        genre_similarities = []
        for idx in range(self.num_items):
            if idx == item_idx:  # Пропускаем тот же самый трек
                genre_similarities.append(-1.0)
                continue
                
            # Получаем жанр текущего трека
            current_genre = self.track_genres.get(idx, 'Unknown')
            
            # Вычисляем сходство с базовым жанром
            sim = self._calculate_genre_distance(base_genre, current_genre)
            genre_similarities.append(sim)
            
        genre_similarities = np.array(genre_similarities)
        
        # Получаем предсказанные рейтинги для пользователя
        scores = self.model.predict(
            user_ids=user_idx,
            item_ids=np.arange(self.num_items),
            item_features=self.item_features
        )
        
        # Комбинируем рейтинги и жанровое сходство
        combined_scores = scores * (0.7 + 0.3 * genre_similarities)
        
        # Исключаем исходный трек
        combined_scores[item_idx] = -float('inf')
        
        # Получаем топ треков
        top_items = np.argsort(-combined_scores)[:n]
        
        return top_items

    def recommend(self, user_id: str, num_recommendations: int = 10) -> List[int]:
        """Генерация рекомендаций для пользователя с улучшенным учетом жанров."""
        try:
            # Проверка существования модели и матрицы взаимодействий
            if self.model is None or self.interaction_matrix is None:
                logger.error("Model is not trained.")
                return []

            if user_id not in self.user_id_map:
                logger.warning(f"User {user_id} not found, returning popular tracks.")
                # Возвращаем популярные треки (по play_count)
                return self._get_popular_tracks(num_recommendations)

            user_idx = self.user_id_map[user_id]
            logger.info(f"User {user_id} mapped to index {user_idx}")

            # Получаем историю прослушиваний пользователя
            user_interactions = self.interaction_matrix.getrow(user_idx).toarray().flatten()
            
            # Определяем наиболее прослушиваемые жанры пользователя
            listened_indices = np.where(user_interactions > 0)[0]
            
            if len(listened_indices) == 0:
                logger.warning(f"User {user_id} has no listening history, returning popular tracks.")
                return self._get_popular_tracks(num_recommendations)
                
            # Определяем предпочитаемые жанры пользователя
            preferred_genres = self._get_preferred_genres(user_id, listened_indices)
            
            # Гибридный подход: комбинируем обычные рекомендации и рекомендации по жанрам
            # 60% обычных рекомендаций, 40% рекомендаций на основе похожих жанров
            standard_count = int(0.6 * num_recommendations)
            genre_based_count = num_recommendations - standard_count
            
            # Обычные рекомендации (коллаборативная фильтрация + контентная)
            logger.info(f"Predicting scores for user_idx={user_idx}, num_items={self.num_items}")
            scores = self.model.predict(
                user_ids=user_idx,
                item_ids=np.arange(self.num_items),
                item_features=self.item_features,
                num_threads=4
            )
            logger.info(f"Predicted scores shape: {scores.shape if hasattr(scores, 'shape') else 'not an array'}")

            # Исключаем треки, которые пользователь уже слушал
            logger.info(f"User interactions shape: {user_interactions.shape}")
            
            # Более безопасный способ создания маски
            listened_mask = np.zeros(len(scores), dtype=bool)
            for i in range(len(user_interactions)):
                if i < len(listened_mask) and user_interactions[i] > 0:
                    listened_mask[i] = True
                    
            logger.info(f"Setting scores to -inf for {listened_mask.sum()} listened tracks")
            scores[listened_mask] = -float('inf')
            
            # Применение бонусов на основе предпочтений жанров
            genre_scores = np.zeros_like(scores)
            for idx in range(len(scores)):
                if idx in self.track_genres:
                    track_genre = self.track_genres[idx]
                    
                    # Суммируем сходство с предпочитаемыми жанрами
                    for preferred_genre, weight in preferred_genres:
                        similarity = self._calculate_genre_distance(track_genre, preferred_genre)
                        genre_scores[idx] += similarity * weight
            
            # Нормализуем жанровые баллы и комбинируем с основными
            if np.max(genre_scores) > 0:
                genre_scores = genre_scores / np.max(genre_scores)
                combined_scores = scores * 0.7 + genre_scores * 0.3 * np.max(scores)
            else:
                combined_scores = scores

            # Получаем топ-N рекомендаций по комбинированным скорам
            logger.info("Computing top items...")
            top_cf_items = np.argsort(-combined_scores)[:standard_count]
            logger.info(f"Top collaborative filtering items: {top_cf_items}")
            
            # Получаем рекомендации на основе жанров для разнообразия
            genre_based_items = []
            
            # Выбираем случайные треки из истории пользователя и ищем похожие
            import random
            sample_size = min(3, len(listened_indices))
            if sample_size > 0:
                seed_tracks = random.sample(list(listened_indices), sample_size)
                
                for seed_idx in seed_tracks:
                    similar_items = self.get_similar_genre_items(user_id, seed_idx, n=5)
                    
                    for item in similar_items:
                        if (len(genre_based_items) < genre_based_count and 
                            item not in genre_based_items and 
                            item not in top_cf_items and 
                            not listened_mask[item]):
                            genre_based_items.append(item)
                            
            logger.info(f"Top genre-based items: {genre_based_items}")
            
            # Объединяем рекомендации
            all_recommended_indices = list(top_cf_items) + genre_based_items
            all_recommended_indices = all_recommended_indices[:num_recommendations]

            # Преобразуем индексы обратно в track_id
            track_ids = []
            reverse_track_map = {idx: tid for tid, idx in self.track_id_map.items()}
            logger.info(f"Reverse track map size: {len(reverse_track_map)}")
            
            for idx in all_recommended_indices:
                if idx in reverse_track_map:
                    track_id = reverse_track_map[idx]
                    track_ids.append(track_id)
                    logger.info(f"Added track_id {track_id} for idx {idx}")
                else:
                    logger.warning(f"Index {idx} not found in reverse_track_map")
            
            logger.info(f"Returning {len(track_ids)} recommendations")
            return track_ids
        except Exception as e:
            logger.error(f"Error in recommend method: {e}", exc_info=True)
            raise
            
    def _get_preferred_genres(self, user_id: str, listened_indices: np.ndarray) -> List[Tuple[str, float]]:
        """Определяет предпочитаемые жанры пользователя на основе истории прослушиваний."""
        if len(listened_indices) == 0:
            return []
            
        # Собираем статистику по жанрам
        genre_counts = {}
        for idx in listened_indices:
            if idx in self.track_genres:
                genre = self.track_genres[idx]
                if genre and genre != 'Unknown':
                    # Разделяем составные жанры
                    genre_parts = re.split(r'[/,&]', genre)
                    for part in genre_parts:
                        part = part.strip()
                        if not part:
                            continue
                        genre_counts[part] = genre_counts.get(part, 0) + 1
        
        # Сортируем жанры по популярности
        sorted_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Нормализуем веса
        total = sum(count for _, count in sorted_genres)
        if total == 0:
            return []
            
        normalized_genres = [(genre, count / total) for genre, count in sorted_genres]
        
        # Возвращаем топ-5 жанров
        return normalized_genres[:5]

    def _get_popular_tracks(self, num_recommendations: int) -> List[int]:
        """Возвращает популярные треки, если пользователь неизвестен."""
        try:
            if self.interaction_matrix is None:
                logger.warning("Interaction matrix is None, returning empty list")
            return []

            # Суммируем play_count по всем пользователям
            logger.info("Calculating popular tracks...")
            play_counts = np.array(self.interaction_matrix.sum(axis=0)).flatten()
            logger.info(f"Play counts shape: {play_counts.shape}")
            
            top_items = np.argsort(-play_counts)[:num_recommendations]
            logger.info(f"Top popular items: {top_items}")

            track_ids = []
            reverse_track_map = {idx: tid for tid, idx in self.track_id_map.items()}
            logger.info(f"Reverse track map has {len(reverse_track_map)} items")
            
            for idx in top_items:
                idx_int = int(idx)  # Убедимся, что idx - целое число
                if idx_int in reverse_track_map:
                    track_id = reverse_track_map[idx_int]
                    track_ids.append(track_id)
                    logger.info(f"Added popular track_id {track_id} for idx {idx_int}")
                else:
                    logger.warning(f"Popular track index {idx_int} not found in reverse_track_map")
            
            logger.info(f"Returning {len(track_ids)} popular tracks")
            return track_ids
        except Exception as e:
            logger.error(f"Error in _get_popular_tracks method: {e}", exc_info=True)
            raise
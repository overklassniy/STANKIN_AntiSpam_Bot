"""
Модуль для работы с ML-моделями.
"""

import json
import os
import pickle
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from dotenv import load_dotenv
from scipy.sparse import hstack

from utils.config import BERT_MODEL, MODELS_DIR
from utils.logging import logger

# Отключаем лишние предупреждения transformers
os.environ["TRANSFORMERS_VERBOSITY"] = "error"

# Загрузка переменных окружения
load_dotenv()

# Ленивая инициализация моделей
_classifier = None
_openai_client = None


def _get_classifier():
    """Ленивая загрузка BERT классификатора."""
    global _classifier
    if _classifier is None:
        try:
            # Импортируем torch явно перед transformers
            # Это необходимо, так как transformers использует torch внутри
            import torch
            # Убеждаемся, что torch доступен
            if not hasattr(torch, '__version__'):
                raise ImportError("torch не установлен корректно")
            
            from transformers import pipeline
            
            logger.info(f"Загрузка BERT модели: {BERT_MODEL}")
            _classifier = pipeline(
                "text-classification",
                model=BERT_MODEL,
                tokenizer=BERT_MODEL,
                device=-1  # CPU
            )
        except ImportError as e:
            logger.error(f"Ошибка импорта torch/transformers: {e}")
            logger.error("Установите зависимости: pip install torch transformers")
            raise RuntimeError(f"Не удалось загрузить ML модели: {e}") from e
        except Exception as e:
            logger.error(f"Ошибка загрузки BERT модели {BERT_MODEL}: {e}")
            raise RuntimeError(f"Не удалось загрузить BERT модель: {e}") from e
    return _classifier


def _get_openai_client():
    """Ленивая инициализация OpenAI клиента."""
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI
        _openai_client = OpenAI()
        logger.info("OpenAI клиент инициализирован")
    return _openai_client


def bert_predict(message: str, threshold: float = 0.5) -> Tuple[int, List[float]]:
    """
    Классифицирует сообщение с помощью BERT модели.

    Args:
        message: Текст сообщения
        threshold: Порог для классификации как спам

    Returns:
        Tuple из (prediction, [prob_ham, prob_spam])
        prediction: 0 - не спам, 1 - спам
    """
    classifier = _get_classifier()

    try:
        result = classifier(message)
        logger.debug(f"BERT результат: {result}")

        # Парсим результат
        prediction = int(result[0]['label'][-1])
        score = result[0]['score']

        # Формируем вероятности
        if prediction == 1:
            probabilities = [1 - score, score]
        else:
            probabilities = [score, 1 - score]

        # Применяем порог
        if probabilities[1] < threshold:
            prediction = 0

        logger.debug(f"BERT: prediction={prediction}, probs={probabilities}")
        return prediction, probabilities

    except Exception as e:
        logger.error(f"Ошибка BERT предсказания: {e}")
        return 0, [0.5, 0.5]


def predict_with_sklearn_model(
    text: str,
    vectorizer: Any,
    scaler: Any,
    model: Any
) -> Tuple[int, List[float]]:
    """
    Предсказание с использованием sklearn модели.

    Args:
        text: Исходный текст
        vectorizer: TF-IDF векторизатор
        scaler: Скейлер для числовых признаков
        model: Sklearn модель

    Returns:
        Tuple из (prediction, probabilities)
    """
    from utils.text import (
        preprocess_text, count_emojis, count_newlines,
        count_whitespaces, count_links, count_tags
    )

    # Предобработка
    text_preprocessed = preprocess_text(text)

    # Векторизация
    text_vector = vectorizer.transform([text_preprocessed])

    # Числовые признаки
    numerical_features = pd.DataFrame([[
        count_emojis(text),
        count_newlines(text),
        count_whitespaces(text),
        count_links(text),
        count_tags(text)
    ]], columns=['emojis', 'newlines', 'whitespaces', 'links', 'tags'])

    # Масштабирование
    numerical_features_scaled = scaler.transform(numerical_features)

    # Объединение признаков
    features = hstack([text_vector, numerical_features_scaled])

    # Предсказание
    prediction = model.predict(features)
    probabilities = model.predict_proba(features)

    return int(prediction[0]), probabilities.tolist()[0]


def get_all_sklearn_predictions(text: str) -> Dict[str, Dict[str, Any]]:
    """
    Получает предсказания от всех sklearn моделей.

    Args:
        text: Текст для классификации

    Returns:
        Словарь {model_name: {prediction, probability}}
    """
    vectorizer_path = f'{MODELS_DIR}/vectorizer.pkl'
    scaler_path = f'{MODELS_DIR}/scaler.pkl'

    predictions = {}

    # Загружаем векторизатор и скейлер
    try:
        with open(vectorizer_path, 'rb') as f:
            vectorizer = pickle.load(f)
        with open(scaler_path, 'rb') as f:
            scaler = pickle.load(f)
    except Exception as e:
        logger.error(f"Ошибка загрузки vectorizer/scaler: {e}")
        return {"error": str(e)}

    # Получаем список моделей
    from utils.helpers import get_pkl_files
    pkl_files = get_pkl_files(MODELS_DIR)

    for model_file in pkl_files:
        if model_file in ['vectorizer.pkl', 'scaler.pkl']:
            continue

        model_path = f'{MODELS_DIR}/{model_file}'
        try:
            with open(model_path, 'rb') as f:
                model = pickle.load(f)

            prediction, probs = predict_with_sklearn_model(text, vectorizer, scaler, model)
            predictions[model_file] = {
                'prediction': prediction,
                'probability': max(probs)
            }
        except Exception as e:
            logger.error(f"Ошибка модели {model_file}: {e}")
            predictions[model_file] = {'error': str(e)}

    return predictions


async def chatgpt_predict(text: str) -> int:
    """
    Проверяет текст на спам с помощью ChatGPT.

    Args:
        text: Текст для проверки

    Returns:
        1 - спам, 0 - не спам, 500 - ошибка
    """
    system_prompt = """Вы - система определения спама в Telegram-чатах. 
Анализируйте сообщения и определяйте, являются ли они спамом.

Характеристики спам-сообщений:
1. Предложения быстрого заработка с нереалистичными суммами
2. Призывы "пишите в ЛС", "ограниченное предложение"
3. Намеренные ошибки или замена букв символами
4. Неконкретные предложения работы без деталей
5. Обещания "легкого заработка", "свободного графика" без сути
6. Избыточное использование эмодзи для привлечения внимания
7. Отсутствие контекста или связи с темой чата

Отвечайте ТОЛЬКО '1' (спам) или '0' (не спам). Без комментариев."""

    try:
        client = _get_openai_client()
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ]
        )
        result = completion.choices[0].message.content.strip()
        logger.info(f"ChatGPT результат: {result}")
        return 1 if '1' in result else 0

    except Exception as e:
        logger.error(f"Ошибка ChatGPT: {e}")
        return 500

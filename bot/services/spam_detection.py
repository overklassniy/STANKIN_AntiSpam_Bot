"""Сервис определения спама через ML-модели.

Содержит:
- BERT-классификатор (ленивая загрузка)
- sklearn-ансамбль (серая зона BERT)
- ChatGPT-проверка (опционально)
"""

import os
import pickle
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd
from dotenv import load_dotenv
from scipy.sparse import hstack

from core.config import MODELS_DIR
from core.logging import logger

os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "1"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"

load_dotenv()

_classifier = None
_classifier_model_name: str | None = None
_openai_client = None


def _get_classifier(model_path: str):
    """Ленивая загрузка BERT классификатора.

    При смене пути модели кеш сбрасывается и модель перезагружается.

    Аргументы:
        model_path (str): Абсолютный путь к директории модели.

    Возвращаемое значение:
        classifier: Pipeline для классификации текста.

    Исключения:
        RuntimeError: Если не удалось загрузить ML-модели.
    """
    global _classifier, _classifier_model_name

    if _classifier is not None and _classifier_model_name == model_path:
        return _classifier

    _classifier = None
    _classifier_model_name = model_path

    try:
        import torch
        if not hasattr(torch, '__version__'):
            raise ImportError("torch не установлен корректно")

        from transformers import pipeline

        logger.info(f"Загрузка BERT модели: {model_path}")
        _classifier = pipeline(
            "text-classification",
            model=model_path,
            tokenizer=model_path,
            device=-1,
        )
    except ImportError as e:
        logger.error(f"Ошибка импорта torch/transformers: {e}")
        logger.error("Установите зависимости: pip install torch transformers")
        raise RuntimeError(f"Не удалось загрузить ML модели: {e}") from e
    except Exception as e:
        logger.error(f"Ошибка загрузки BERT модели {model_path}: {e}")
        raise RuntimeError(f"Не удалось загрузить BERT модель: {e}") from e
    return _classifier


def _get_openai_client():
    """Ленивая инициализация OpenAI клиента.

    Возвращаемое значение:
        client (OpenAI): Экземпляр клиента OpenAI.
    """
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI
        _openai_client = OpenAI()
        logger.info("OpenAI клиент инициализирован")
    return _openai_client


def predict_spam(message: str, model_path: str, threshold: float = 0.5) -> Tuple[int, List[float]]:
    """Классифицирует сообщение с помощью BERT модели.

    Аргументы:
        message (str): Текст сообщения.
        model_path (str): Абсолютный путь к директории модели.
        threshold (float): Порог для классификации как спам.

    Возвращаемое значение:
        Tuple[int, List[float]]: (prediction, [prob_ham, prob_spam]).
        prediction: 0 — не спам, 1 — спам.
    """
    classifier = _get_classifier(model_path)

    try:
        result = classifier(message)

        prediction = int(result[0]['label'][-1])
        score = result[0]['score']

        if prediction == 1:
            probabilities = [1 - score, score]
        else:
            probabilities = [score, 1 - score]

        if probabilities[1] < threshold:
            prediction = 0

        logger.info(f"BERT: prediction={prediction}, prob_spam={probabilities[1]:.4f}, prob_ham={probabilities[0]:.4f}")
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
    """Предсказание с использованием sklearn модели.

    Аргументы:
        text (str): Исходный текст.
        vectorizer (Any): TF-IDF векторизатор.
        scaler (Any): Скейлер для числовых признаков.
        model (Any): Sklearn модель.

    Возвращаемое значение:
        Tuple[int, List[float]]: (prediction, probabilities).
    """
    from bot.services.text_analysis import (
        preprocess_text, count_emojis, count_newlines,
        count_whitespaces, count_links, count_tags
    )

    text_preprocessed = preprocess_text(text)
    text_vector = vectorizer.transform([text_preprocessed])

    numerical_features = pd.DataFrame([[
        count_emojis(text),
        count_newlines(text),
        count_whitespaces(text),
        count_links(text),
        count_tags(text)
    ]], columns=['emojis', 'newlines', 'whitespaces', 'links', 'tags'])

    numerical_features_scaled = scaler.transform(numerical_features)
    features = hstack([text_vector, numerical_features_scaled])

    prediction = model.predict(features)
    probabilities = model.predict_proba(features)

    return int(prediction[0]), probabilities.tolist()[0]


def get_all_sklearn_predictions(text: str) -> Dict[str, Dict[str, Any]]:
    """Получает предсказания от всех sklearn моделей.

    Аргументы:
        text (str): Текст для классификации.

    Возвращаемое значение:
        Dict[str, Dict[str, Any]]: Словарь {model_name: {prediction, probability}}.
    """
    vectorizer_path = f'{MODELS_DIR}/vectorizer.pkl'
    scaler_path = f'{MODELS_DIR}/scaler.pkl'

    predictions = {}

    try:
        with open(vectorizer_path, 'rb') as f:
            vectorizer = pickle.load(f)
        with open(scaler_path, 'rb') as f:
            scaler = pickle.load(f)
    except Exception as e:
        logger.error(f"Ошибка загрузки vectorizer/scaler: {e}")
        return {"error": str(e)}

    from core.utils import get_pkl_files
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


def ensemble_confirm_spam(text: str, min_models: int = 2) -> bool:
    """Проверяет через sklearn-ансамбль, подтверждается ли спам.

    Используется в серой зоне BERT (0.94-0.98).

    Аргументы:
        text (str): Текст сообщения.
        min_models (int): Минимальное число моделей, подтверждающих спам.

    Возвращаемое значение:
        bool: True если достаточное число моделей подтвердили спам.
    """
    try:
        predictions = get_all_sklearn_predictions(text)
        if 'error' in predictions:
            logger.warning("Ансамбль: ошибка получения sklearn-предсказаний")
            return False

        spam_votes = sum(
            1 for name, pred in predictions.items()
            if isinstance(pred, dict) and 'prediction' in pred and pred['prediction'] == 1
        )
        total = sum(
            1 for name, pred in predictions.items()
            if isinstance(pred, dict) and 'prediction' in pred
        )

        logger.debug(f"Ансамбль: {spam_votes}/{total} моделей голосуют за спам")
        return spam_votes >= min_models
    except Exception as e:
        logger.error(f"Ошибка ансамблирования: {e}")
        return False


async def check_spam_chatgpt(text: str) -> int:
    """Проверяет текст на спам с помощью ChatGPT.

    Аргументы:
        text (str): Текст для проверки.

    Возвращаемое значение:
        int: 1 — спам, 0 — не спам, 500 — ошибка.
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

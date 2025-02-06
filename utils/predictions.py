import json
import os
import pickle
from typing import Tuple, List, Any

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI
from scipy.sparse import hstack

os.environ["TRANSFORMERS_VERBOSITY"] = "error"
from transformers import pipeline

from utils.basic import config, get_pkl_files, logger
from utils.preprocessing import (
    preprocess_text,
    count_emojis,
    count_newlines,
    count_whitespaces,
    count_links,
    count_tags
)

# Загрузка переменных окружения
load_dotenv()
logger.info("Переменные окружения успешно загружены.")

models_dir = config['MODELS_DIR']

bert_model = config['BERT_MODEL']
tokenizer = config['BERT_MODEL']

# Инициализация пайплайна классификатора на основе BERT
logger.info("Инициализация пайплайна классификатора BERT с моделью: %s", bert_model)
classifier = pipeline("text-classification", model=bert_model, tokenizer=tokenizer)

# Инициализация клиента OpenAI
client = OpenAI()
logger.info("Клиент OpenAI успешно инициализирован.")


def bert_predict(message: str, threshold: float = 0.5) -> Tuple[int, List[float]]:
    """
    Генерирует предсказание с помощью модели BERT для заданного сообщения.

    Аргументы:
        message (str): Сообщение для анализа.
        threshold (float): Пороговое значение для принятия предсказания.

    Возвращает:
        tuple[int, list[float]]: Предсказание (0 или 1) и список вероятностей.
    """
    logger.info("Запуск предсказания BERT для сообщения: %s", message)
    result = classifier(message)
    logger.debug("Результат классификации: %s", result)

    # Извлечение метки предсказания (ожидается, что метка заканчивается цифрой)
    prediction = int(result[0]['label'][-1])
    score = result[0]['score']
    probabilities = []
    if prediction == 1:
        probabilities = [1 - score, score]
    elif prediction == 0:
        probabilities = [score, 1 - score]

    logger.debug("Начальное предсказание: %s, вероятности: %s", prediction, probabilities)

    if probabilities[1] < threshold:
        logger.info("Вероятность %s ниже порога %s. Изменение предсказания на 0.", probabilities[1], threshold)
        prediction = 0

    logger.info("Предсказание BERT завершено. Итоговое предсказание: %s, вероятности: %s", prediction, probabilities)
    return prediction, probabilities


def predict_message(text: str, vectorizer: Any, scaler: Any, model: Any) -> Tuple[int, List[float]]:
    """
    Предсказывает метку и вероятности для заданного текста с использованием модели машинного обучения.

    Аргументы:
        text (str): Входной текст для анализа.
        vectorizer: Векторизатор для преобразования текста.
        scaler: Масштабатор числовых признаков.
        model: Модель машинного обучения.

    Возвращает:
        tuple[int, list[float]]: Метка предсказания и список вероятностей.
    """
    logger.info("Запуск предсказания для текста: %s", text)
    # Предварительная обработка текста
    text_preprocessed = preprocess_text(text)
    logger.debug("Текст после предварительной обработки: %s", text_preprocessed)

    # Векторизация текста
    text_vector = vectorizer.transform([text_preprocessed])
    logger.debug("Текст в векторном виде получен.")

    # Создание числовых признаков
    numerical_features = pd.DataFrame(
        [[
            count_emojis(text),
            count_newlines(text),
            count_whitespaces(text),
            count_links(text),
            count_tags(text)
        ]],
        columns=['emojis', 'newlines', 'whitespaces', 'links', 'tags']
    )
    logger.debug("Числовые признаки сформированы: %s", numerical_features.to_dict())

    # Масштабирование числовых признаков
    numerical_features_scaled = scaler.transform(numerical_features)
    logger.debug("Числовые признаки масштабированы.")

    # Объединение текстовых и числовых признаков
    features = hstack([text_vector, numerical_features_scaled])
    logger.debug("Признаки объединены для предсказания.")

    # Предсказание
    prediction = model.predict(features)
    probabilities = model.predict_proba(features)
    logger.info("Модель предсказала метку: %s с вероятностями: %s", prediction, probabilities)
    return int(prediction[0]), probabilities.tolist()[0]


def get_predictions(text: str) -> str:
    """
    Генерирует предсказания для заданного текста, используя загруженные модели.

    Аргументы:
        text (str): Входной текст для анализа.

    Возвращает:
        str: Предсказания в формате JSON.
    """
    logger.info("Получение предсказаний для текста: %s", text)
    vectorizer_path = f'{models_dir}/vectorizer.pkl'
    scaler_path = f'{models_dir}/scaler.pkl'
    models_dir_files = get_pkl_files(models_dir)
    logger.debug("Найденные файлы в модели директории: %s", models_dir_files)

    # Загрузка векторизатора
    try:
        with open(vectorizer_path, 'rb') as vectorizer_file:
            vectorizer = pickle.load(vectorizer_file)
        logger.info("Векторизатор успешно загружен из %s", vectorizer_path)
    except Exception as e:
        logger.error("Ошибка загрузки векторизатора: %s", e)
        return json.dumps({"error": "Ошибка загрузки векторизатора"})

    # Загрузка масштабатора
    try:
        with open(scaler_path, 'rb') as scaler_file:
            scaler = pickle.load(scaler_file)
        logger.info("Масштабатор успешно загружен из %s", scaler_path)
    except Exception as e:
        logger.error("Ошибка загрузки масштабатора: %s", e)
        return json.dumps({"error": "Ошибка загрузки масштабатора"})

    predictions = {}

    for model_path in models_dir_files:
        if model_path in ['vectorizer.pkl', 'scaler.pkl']:
            logger.debug("Пропуск файла: %s", model_path)
            continue

        model_path_f = f'{models_dir}/{model_path}'
        logger.info("Загрузка модели из файла: %s", model_path_f)
        try:
            with open(model_path_f, 'rb') as model_file:
                model = pickle.load(model_file)
            logger.info("Модель успешно загружена: %s", model_path)
        except Exception as e:
            logger.error("Ошибка загрузки модели %s: %s", model_path, e)
            continue

        # Предсказание
        try:
            prediction, probabilities = predict_message(text, vectorizer, scaler, model)
            probability = max(probabilities)
            predictions[model_path] = {'prediction': prediction, 'probability': probability}
            logger.info("Для модели %s получено предсказание: %s, вероятность: %s", model_path, prediction, probability)
        except Exception as e:
            logger.error("Ошибка при предсказании модели %s: %s", model_path, e)
            predictions[model_path] = {'error': str(e)}

    # Преобразование предсказаний в формат JSON
    try:
        parsed = json.loads(json.dumps(predictions))
        output = json.dumps(parsed, indent=4)
        logger.info("Предсказания успешно преобразованы в формат JSON.")
        return output
    except Exception as e:
        logger.error("Ошибка при преобразовании предсказаний в JSON: %s", e)
        return json.dumps({"error": "Ошибка преобразования предсказаний"})


async def chatgpt_predict(text: str) -> int:
    """
    Проверяет текст на наличие спама с использованием модели GPT.

    Аргументы:
        text (str): Текст сообщения для проверки.

    Возвращает:
        int: 1, если текст является спамом, 0 если нет, 500 в случае ошибки.
    """
    logger.info("Запуск предсказания ChatGPT для текста: %s", text)
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": (
                    "Вы - система определения спама в чатах Telegram. Ваша задача - анализировать сообщения и определять, "
                    "являются ли они спамом. \n\n"
                    "Характеристики спам-сообщений:\n"
                    "1. Предложения быстрого заработка с нереалистично высокими суммами.\n"
                    "2. Призывы к действию типа 'пишите в личные сообщения', 'ограниченное предложение'.\n"
                    "3. Намеренные орфографические ошибки или замена букв символами (например, 'сOoбщение' вместо 'сообщение').\n"
                    "4. Неконкретные предложения работы без деталей.\n"
                    "5. Обещания легкого заработка, 'свободного графика' без объяснения сути работы.\n"
                    "6. Использование эмодзи или необычных символов для привлечения внимания.\n"
                    "7. Отсутствие контекста или связи с предыдущими сообщениями в чате.\n\n"
                    "Отвечайте только '1', если сообщение соответствует характеристикам спама, или '0', если это обычное сообщение. "
                    "Не добавляйте никаких дополнительных комментариев или объяснений."
                )},
                {"role": "user", "content": text}
            ]
        )
        result = completion.choices[0].message.content.strip().upper()
        logger.info("ChatGPT вернул результат: %s", result)
        return 1 if '1' in result else 0
    except Exception as e:
        logger.error("Ошибка при проверке на спам через ChatGPT: %s", e)
        return 500

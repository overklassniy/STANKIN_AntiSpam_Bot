import json
import pickle

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI
from scipy.sparse import hstack
from transformers import pipeline

from basic import config, get_pkl_files, logger
from preprocessing import preprocess_text, count_emojis, count_whitespaces, count_links, count_tags

models_dir = config['MODELS_DIR']

bert_model = config['BERT_MODEL']
tokenizer = config['BERT_MODEL']

# Инициализация пайплайна классификатора на основе BERT
classifier = pipeline("text-classification", model=bert_model, tokenizer=tokenizer)

# Загрузка переменных окружения
load_dotenv()

# Инициализация клиента OpenAI
client = OpenAI()


def bert_predict(message: str, threshold: float = 0.5) -> tuple[int, list[float]]:
    """
    Функция для предсказания с помощью модели BERT.

    Параметры:
        message (str): – входное сообщение для анализа
        threshold (float): – пороговое значение для предсказания класса

    Возвращает:
        tuple[int, list[float]] - предсказание (0 или 1) и список вероятностей
    """
    result = classifier(message)

    prediction = int(result[0]['label'][-1])  # Извлечение метки предсказания
    score = result[0]['score']  # Вероятность предсказания
    probabilities = []
    if prediction == 1:
        probabilities = [1 - score, score]
    elif prediction == 0:
        probabilities = [score, 1 - score]

    if max(probabilities) < threshold:
        prediction = abs(prediction - 1)

    return prediction, probabilities


def predict_message(text: str, vectorizer, scaler, model) -> tuple[int, list[float]]:
    """
    Предсказывает метку и вероятности для текста с использованием модели машинного обучения.

    Параметры:
        text (str): - входной текст для анализа
        vectorizer: - векторизатор для преобразования текста
        scaler: - масштабатор числовых признаков
        model: - модель машинного обучения

    Возвращает:
        tuple[int, list[float]] - метка предсказания и вероятности
    """
    # Предварительная обработка текста
    text_preprocessed = preprocess_text(text)

    # Векторизация текста
    text_vector = vectorizer.transform([text_preprocessed])

    # Создание числовых признаков
    numerical_features = pd.DataFrame(
        [[count_emojis(text), count_whitespaces(text), count_links(text), count_tags(text)]],
        columns=['emojis', 'whitespaces', 'links', 'tags']
    )
    # Масштабирование числовых признаков
    numerical_features_scaled = scaler.transform(numerical_features)

    # Объединение текстовых и числовых признаков
    features = hstack([text_vector, numerical_features_scaled])

    # Предсказание
    prediction = model.predict(features)
    probabilities = model.predict_proba(features)
    return int(prediction[0]), *probabilities.tolist()


def get_predictions(text: str) -> str:
    """
    Генерирует предсказания для текста, используя загруженные модели.

    Параметры:
        text (str): - входной текст для анализа

    Возвращает:
        str - предсказания в формате JSON
    """
    vectorizer_path = f'{models_dir}/vectorizer.pkl'
    scaler_path = f'{models_dir}/scaler.pkl'
    models_dir_files = get_pkl_files(models_dir)

    # Загрузка векторизатора
    with open(vectorizer_path, 'rb') as vectorizer_file:
        vectorizer = pickle.load(vectorizer_file)

    # Загрузка масштабатора
    with open(scaler_path, 'rb') as scaler_file:
        scaler = pickle.load(scaler_file)

    predictions = {}

    for model_path in models_dir_files:
        if model_path in ['vectorizer.pkl', 'scaler.pkl']:
            continue

        model_path_f = f'{models_dir}/{model_path}'

        # Загрузка модели
        with open(model_path_f, 'rb') as model_file:
            model = pickle.load(model_file)

        # Предсказание
        prediction, probabilities = predict_message(text, vectorizer, scaler, model)
        probability = max(probabilities)
        predictions[model_path] = {'prediction': prediction, 'probability': probability}

    # Преобразование предсказаний в читаемый JSON формат
    parsed = json.loads(str(predictions).replace("'", '"'))
    return str(json.dumps(parsed, indent=4))


async def chatgpt_predict(text: str) -> int:
    """
    Проверяет текст на наличие спама с использованием модели GPT.

    Параметры:
        text (str): - текст сообщения для проверки

    Возвращает:
        int: 1, если текст является спамом, иначе 0. Возвращает 500 в случае ошибки.
    """
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": """
Вы - система определения спама в чатах Telegram. Ваша задача - анализировать сообщения и определять, являются ли они спамом. 

Характеристики спам-сообщений:
1. Предложения быстрого заработка с нереалистично высокими суммами.
2. Призывы к действию типа "пишите в личные сообщения", "ограниченное предложение".
3. Намеренные орфографические ошибки или замена букв символами (например, "сOoбщение" вместо "сообщение").
4. Неконкретные предложения работы без деталей.
5. Обещания легкого заработка, "свободного графика" без объяснения сути работы.
6. Использование эмодзи или необычных символов для привлечения внимания.
7. Отсутствие контекста или связи с предыдущими сообщениями в чате.

Проанализируйте предоставленное сообщение и определите, является ли оно спамом на основе этих критериев. 

Отвечайте только "1", если сообщение соответствует характеристикам спама, или "0", если это обычное сообщение. Не добавляйте никаких дополнительных комментариев или объяснений.
                """},
                {"role": "user", "content": text}
            ]
        )
        result = completion.choices[0].message.content.strip().upper()
        return 1 if '1' in result else 0
    except Exception as e:
        logger.error(f"Ошибка при проверке на спам: {e}")
        return 500

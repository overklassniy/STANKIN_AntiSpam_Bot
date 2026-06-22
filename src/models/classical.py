"""
Модуль обучения классических ML-моделей.

Содержит функции для подготовки признаков (word TF-IDF, char TF-IDF, числовые),
обучения Logistic Regression, Naive Bayes, Random Forest, LightGBM, CatBoost
с балансировкой классов через class_weight, а также функцию предсказания на новых данных.
"""

import pickle
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.sparse import hstack
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.preprocessing import StandardScaler

try:
    from lightgbm import LGBMClassifier
except ImportError:
    LGBMClassifier = None

try:
    from catboost import CatBoostClassifier
except ImportError:
    CatBoostClassifier = None

import nltk
from nltk.corpus import stopwords

from src.config import MODELS_DIR
from src.data.preprocessing import preprocess_text
from src.features.extractors import (
    avg_word_length,
    capital_ratio,
    count_digits,
    count_emojis,
    count_exclamation,
    count_html_tags,
    count_links,
    count_newlines,
    count_phone_numbers,
    count_punctuation,
    count_tags,
    count_whitespaces,
    emoji_diversity,
    has_crypto_mention,
    has_markdown_formatting,
    repeat_char_ratio,
    unique_word_ratio,
    url_ratio,
    word_count,
)

NUMERICAL_COLUMNS = [
    "emojis",
    "newlines",
    "whitespaces",
    "links",
    "tags",
    "length",
    "capital_ratio",
    "punctuation_count",
    "digit_count",
    "avg_word_length",
    "word_count",
    "unique_word_ratio",
    "repeat_char_ratio",
    "phone_count",
    "has_crypto",
    "exclamation_count",
    "url_ratio",
    "html_tag_count",
    "has_markdown",
    "emoji_diversity",
]


def _get_combined_stopwords() -> list[str]:
    """
    Получает объединённый список русских и английских стоп-слов.

    Возвращаемое значение:
        list[str]: Список стоп-слов.
    """
    nltk.download("stopwords", quiet=True)
    russian_stopwords = set(stopwords.words("russian"))
    english_stopwords = set(ENGLISH_STOP_WORDS)
    return list(russian_stopwords.union(english_stopwords))


def prepare_features(
    df_train: pd.DataFrame,
    df_test: pd.DataFrame | None = None,
    random_state: int = 42,
    tfidf_max_features: int = 5000,
    use_char_tfidf: bool = True,
    char_tfidf_max_features: int = 2000,
):
    """
    Подготавливает текстовые и числовые признаки для обучения.

    Если передан df_test, используется он в качестве тестовой выборки.
    Иначе df_train разделяется через train_test_split.

    Аргументы:
        df_train (pd.DataFrame): DataFrame с колонками text_preprocessed, label и числовыми признаками.
        df_test (pd.DataFrame | None): Тестовый DataFrame. Если None, используется split.
        random_state (int): Seed для воспроизводимости.
        tfidf_max_features (int): Максимальное количество признаков word TF-IDF.
        use_char_tfidf (bool): Использовать ли char-level TF-IDF.
        char_tfidf_max_features (int): Максимальное количество признаков char TF-IDF.

    Возвращаемое значение:
        tuple: (X_train, X_test, y_train, y_test,
                vectorizer, char_vectorizer, scaler,
                X_train_nc, X_test_nc)
    """
    train_texts = list(df_train["text_preprocessed"])
    train_labels = list(df_train["label"])
    train_num = list(df_train[NUMERICAL_COLUMNS].values)

    if df_test is not None:
        test_texts = list(df_test["text_preprocessed"])
        test_labels = list(df_test["label"])
        test_num = list(df_test[NUMERICAL_COLUMNS].values)
    else:
        train_texts, test_texts, train_labels, test_labels = train_test_split(
            train_texts, train_labels, test_size=0.2,
            random_state=random_state, stratify=train_labels,
        )
        train_num, test_num = train_test_split(
            train_num, test_size=0.2,
            random_state=random_state, stratify=train_labels,
        )

    combined_stopwords = _get_combined_stopwords()

    vectorizer = TfidfVectorizer(
        max_features=tfidf_max_features,
        ngram_range=(1, 2),
        stop_words=combined_stopwords,
        min_df=2,
        sublinear_tf=True,
    )
    word_features_train = vectorizer.fit_transform(train_texts)
    word_features_test = vectorizer.transform(test_texts)

    char_vectorizer = None
    char_features_train = None
    char_features_test = None
    if use_char_tfidf:
        char_vectorizer = TfidfVectorizer(
            max_features=char_tfidf_max_features,
            ngram_range=(2, 5),
            analyzer="char_wb",
            min_df=2,
            sublinear_tf=True,
        )
        char_features_train = char_vectorizer.fit_transform(train_texts)
        char_features_test = char_vectorizer.transform(test_texts)

    numerical_features_train = pd.DataFrame(train_num, columns=NUMERICAL_COLUMNS)
    numerical_features_test = pd.DataFrame(test_num, columns=NUMERICAL_COLUMNS)

    scaler = StandardScaler()
    numerical_features_train_scaled = scaler.fit_transform(numerical_features_train)
    numerical_features_test_scaled = scaler.transform(numerical_features_test)

    train_parts = [word_features_train]
    test_parts = [word_features_test]
    if char_features_train is not None:
        train_parts.append(char_features_train)
        test_parts.append(char_features_test)
    train_parts.append(numerical_features_train_scaled)
    test_parts.append(numerical_features_test_scaled)

    X_train = hstack(train_parts).tocsr()
    X_test = hstack(test_parts).tocsr()

    # Признаки без масштабирования для Naive Bayes
    nc_train_parts = [word_features_train]
    nc_test_parts = [word_features_test]
    if char_features_train is not None:
        nc_train_parts.append(char_features_train)
        nc_test_parts.append(char_features_test)
    nc_train_parts.append(np.array(train_num))
    nc_test_parts.append(np.array(test_num))

    X_train_nc = hstack(nc_train_parts).tocsr()
    X_test_nc = hstack(nc_test_parts).tocsr()

    return (
        X_train, X_test, train_labels, test_labels,
        vectorizer, char_vectorizer, scaler,
        X_train_nc, X_test_nc,
    )


def train_classical_models(
    X_train, y_train,
    X_train_nc,
    random_state: int = 42,
) -> dict[str, Any]:
    """
    Обучает набор классических моделей: LR, RF, NB, LightGBM, CatBoost.

    Все модели используют class_weight='balanced' вместо SMOTE,
    так как SMOTE на разреженных TF-IDF признаках создаёт
    нерепрезентативные синтетические примеры.

    Аргументы:
        X_train: Признаки обучающей выборки (масштабированные).
        y_train: Метки обучающей выборки.
        X_train_nc: Признаки без масштабирования (для NB).
        random_state (int): Seed для воспроизводимости.

    Возвращаемое значение:
        dict[str, Any]: Словарь с обученными моделями.
    """
    models = {}

    models["lr"] = LogisticRegression(class_weight="balanced", max_iter=2000, random_state=random_state)
    models["lr"].fit(X_train, y_train)

    models["rf"] = RandomForestClassifier(class_weight="balanced", random_state=random_state, n_estimators=100)
    models["rf"].fit(X_train, y_train)

    models["nb"] = MultinomialNB()
    models["nb"].fit(X_train_nc, y_train)

    if LGBMClassifier is not None:
        models["lgbm"] = LGBMClassifier(
            class_weight="balanced",
            n_estimators=300,
            max_depth=7,
            learning_rate=0.05,
            random_state=random_state,
            verbose=-1,
            n_jobs=-1,
        )
        models["lgbm"].fit(X_train, y_train)
        # LightGBM создаёт feature_names_in_ как property без возможности удаления,
        # что вызывает варнинг sklearn при predict на разреженных матрицах.
        warnings.filterwarnings(
            "ignore",
            message="X does not have valid feature names",
            category=UserWarning,
            module="sklearn.utils.validation",
        )

    if CatBoostClassifier is not None:
        models["catboost"] = CatBoostClassifier(
            auto_class_weights="Balanced",
            iterations=500,
            depth=6,
            learning_rate=0.03,
            random_state=random_state,
            verbose=0,
        )
        models["catboost"].fit(X_train, y_train)

    return models


def predict_message(
    text: str,
    vectorizer,
    scaler,
    model,
    char_vectorizer=None,
) -> tuple[int, list[float]]:
    """
    Предсказывает метку и вероятности для текста с использованием классической модели.

    Аргументы:
        text (str): Входной текст для анализа.
        vectorizer: Word TF-IDF векторизатор.
        scaler: Масштабатор числовых признаков.
        model: Обученная модель.
        char_vectorizer: Char TF-IDF векторизатор (опционально).

    Возвращаемое значение:
        tuple[int, list[float]]: Метка предсказания и вероятности классов.
    """
    text_preprocessed = preprocess_text(text)
    text_vector = vectorizer.transform([text_preprocessed])
    numerical_features = pd.DataFrame(
        [[
            count_emojis(text),
            count_newlines(text),
            count_whitespaces(text),
            count_links(text),
            count_tags(text),
            len(text),
            capital_ratio(text),
            count_punctuation(text),
            count_digits(text),
            avg_word_length(text),
            word_count(text),
            unique_word_ratio(text),
            repeat_char_ratio(text),
            count_phone_numbers(text),
            has_crypto_mention(text),
            count_exclamation(text),
            url_ratio(text),
            count_html_tags(text),
            has_markdown_formatting(text),
            emoji_diversity(text),
        ]],
        columns=NUMERICAL_COLUMNS,
    )
    numerical_features_scaled = scaler.transform(numerical_features)

    parts = [text_vector]
    if char_vectorizer is not None:
        char_vector = char_vectorizer.transform([text_preprocessed])
        parts.append(char_vector)
    parts.append(numerical_features_scaled)

    features = hstack(parts).tocsr()
    prediction = model.predict(features)
    probabilities = model.predict_proba(features)
    return int(prediction[0]), probabilities.tolist()[0]


def save_models(
    models: dict[str, Any],
    vectorizer,
    scaler,
    char_vectorizer=None,
    output_dir: str | Path | None = None,
) -> None:
    """
    Сохраняет обученные модели, векторизаторы и масштабатор в pickle-файлы.

    Аргументы:
        models (dict): Словарь с обученными моделями.
        vectorizer: Word TF-IDF векторизатор.
        scaler: Масштабатор числовых признаков.
        char_vectorizer: Char TF-IDF векторизатор (опционально).
        output_dir (str | Path | None): Директория для сохранения. По умолчанию MODELS_DIR.
    """
    output_dir = Path(output_dir) if output_dir else MODELS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "vectorizer.pkl", "wb") as f:
        pickle.dump(vectorizer, f)
    with open(output_dir / "scaler.pkl", "wb") as f:
        pickle.dump(scaler, f)
    if char_vectorizer is not None:
        with open(output_dir / "char_vectorizer.pkl", "wb") as f:
            pickle.dump(char_vectorizer, f)

    name_to_filename = {
        "lr": "lr_model.pkl",
        "rf": "rf_model.pkl",
        "nb": "nb_model.pkl",
        "lgbm": "lgbm_model.pkl",
        "catboost": "catboost_model.pkl",
    }
    for name, model in models.items():
        filename = name_to_filename.get(name, f"{name}_model.pkl")
        with open(output_dir / filename, "wb") as f:
            pickle.dump(model, f)

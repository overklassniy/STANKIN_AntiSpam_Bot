"""
Модуль оценки качества моделей.

Содержит функцию оптимизации порога классификации для максимизации Precision
при заданном Recall.
"""

import numpy as np
import pandas as pd
from sklearn.metrics import precision_recall_curve


def optimize_threshold(
    y_true: np.ndarray | pd.Series,
    y_proba: np.ndarray | pd.Series,
    target_recall: float = 0.90,
) -> dict[str, float]:
    """
    Находит оптимальный порог классификации для максимизации Precision при заданном Recall.

    Алгоритм работы:
        1. Построить PR-кривую.
        2. Найти все пороги, где Recall >= target_recall.
        3. Выбрать порог с максимальным Precision среди них.

    Аргументы:
        y_true: Истинные метки (0 или 1).
        y_proba: Вероятности класса 1.
        target_recall (float): Минимально допустимый Recall.

    Возвращаемое значение:
        dict: Словарь с ключами threshold, precision, recall.
    """
    y_true = np.asarray(y_true)
    y_proba = np.asarray(y_proba)
    precision, recall, thresholds = precision_recall_curve(y_true, y_proba)
    valid_mask = recall >= target_recall
    if not valid_mask.any():
        best_idx = np.argmax(recall)
    else:
        best_idx = np.argmax(precision[valid_mask])
        valid_indices = np.where(valid_mask)[0]
        best_idx = valid_indices[best_idx]
    if best_idx < len(thresholds):
        best_threshold = thresholds[best_idx]
    else:
        best_threshold = 0.5
    return {
        "threshold": float(best_threshold),
        "precision": float(precision[best_idx]),
        "recall": float(recall[best_idx]),
    }

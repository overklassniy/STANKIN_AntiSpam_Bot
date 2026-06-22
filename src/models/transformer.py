"""
Модуль дообучения трансформерных моделей для классификации спама.

Содержит класс FocalLossTrainer, функции токенизации,
вычисления метрик, батчевого предсказания, температурного масштабирования,
поддержки FP16, конфигурации моделей, замера CPU-инференса и подготовки
вариантов текста для обучения.
"""

import time
from typing import Any

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from transformers import Trainer


class FocalLossTrainer(Trainer):
    """Trainer с Focal Loss для лучшей работы с hard examples и несбалансированными классами."""

    def __init__(self, focal_alpha: float = 0.25, focal_gamma: float = 2.0, **kwargs: Any):
        """
        Инициализирует FocalLossTrainer.

        Аргументы:
            focal_alpha (float): Весовой коэффициент для Focal Loss.
            focal_gamma (float): Параметр фокусировки для Focal Loss.
            **kwargs: Дополнительные аргументы для Trainer.
        """
        super().__init__(**kwargs)
        self.focal_alpha = focal_alpha
        self.focal_gamma = focal_gamma

    def compute_loss(self, model, inputs, return_outputs: bool = False, **kwargs: Any):
        """
        Вычисляет Focal Loss для батча.

        Аргументы:
            model: Модель для обучения.
            inputs: Входные данные батча.
            return_outputs (bool): Возвращать ли выходы модели вместе с loss.
            **kwargs: Дополнительные аргументы.
        """
        labels = inputs.pop("labels")
        outputs = model(**inputs)
        logits = outputs.logits
        ce_loss = F.cross_entropy(logits, labels, reduction="none")
        pt = torch.exp(-ce_loss)
        focal_loss = self.focal_alpha * (1 - pt) ** self.focal_gamma * ce_loss
        loss = focal_loss.mean()
        return (loss, outputs) if return_outputs else loss


class TemperatureScaler(nn.Module):
    """Температурное масштабирование для калибровки вероятностей BERT модели."""

    def __init__(self):
        """Инициализирует TemperatureScaler с температурой 1.0."""
        super().__init__()
        self.temperature = nn.Parameter(torch.ones(1))

    def forward(self, logits: torch.Tensor) -> torch.Tensor:
        """
        Масштабирует логиты температурой.

        Аргументы:
            logits (torch.Tensor): Логиты модели.

        Возвращаемое значение:
            torch.Tensor: Отмасштабированные логиты.
        """
        return logits / self.temperature

    def fit(self, logits: torch.Tensor, labels: torch.Tensor, max_iter: int = 100, lr: float = 0.01):
        """
        Обучает температуру на валидационных логитах.

        Аргументы:
            logits (torch.Tensor): Логиты модели на валидационной выборке.
            labels (torch.Tensor): Истинные метки.
            max_iter (int): Количество итераций оптимизации.
            lr (float): Learning rate.
        """
        optimizer = torch.optim.LBFGS([self.temperature], lr=lr, max_iter=max_iter)
        criterion = nn.CrossEntropyLoss()

        def closure():
            optimizer.zero_grad()
            scaled_logits = self.forward(logits)
            loss = criterion(scaled_logits, labels)
            loss.backward()
            return loss

        optimizer.step(closure)


def get_training_args(
    output_dir: str = "rb_results",
    learning_rate: float = 2e-5,
    num_train_epochs: int = 7,
    per_device_train_batch_size: int = 16,
    per_device_eval_batch_size: int = 16,
    max_length: int = 256,
    fp16: bool = True,
    gradient_checkpointing: bool | None = None,
    **kwargs: Any,
):
    """
    Создаёт TrainingArguments с поддержкой FP16 и настраиваемыми параметрами.

    Аргументы:
        output_dir (str): Директория для результатов.
        learning_rate (float): Learning rate.
        num_train_epochs (int): Количество эпох.
        per_device_train_batch_size (int): Размер батча для обучения.
        per_device_eval_batch_size (int): Размер батча для оценки.
        max_length (int): Максимальная длина последовательности.
        fp16 (bool): Использовать ли FP16 (mixed precision).
        gradient_checkpointing (bool | None): Включить gradient checkpointing.
            Если None, определяется автоматически: включается при fp16 и max_length > 256.
        **kwargs: Дополнительные аргументы для TrainingArguments.

    Возвращаемое значение:
        TrainingArguments: Настроенные аргументы обучения.
    """
    from transformers import TrainingArguments

    if gradient_checkpointing is None:
        gradient_checkpointing = fp16 and max_length > 256

    return TrainingArguments(
        output_dir=output_dir,
        eval_strategy="epoch",
        save_strategy="epoch",
        learning_rate=learning_rate,
        per_device_train_batch_size=per_device_train_batch_size,
        per_device_eval_batch_size=per_device_eval_batch_size,
        num_train_epochs=num_train_epochs,
        weight_decay=0.01,
        lr_scheduler_type="cosine",
        warmup_ratio=0.1,
        logging_dir=f"{output_dir}_logs",
        logging_strategy="no",
        save_total_limit=2,
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        greater_is_better=True,
        fp16=fp16,
        gradient_checkpointing=gradient_checkpointing,
        disable_tqdm=False,
        **kwargs,
    )


def tokenize_function(examples: dict, tokenizer, max_length: int = 256) -> dict:
    """
    Токенизирует тексты для модели RuBERT.

    Аргументы:
        examples (dict): Словарь с ключом "text".
        tokenizer: Токенизатор HuggingFace.
        max_length (int): Максимальная длина последовательности.

    Возвращаемое значение:
        dict: Токенизированные данные.
    """
    return tokenizer(
        examples["text"],
        padding="max_length",
        truncation=True,
        max_length=max_length,
    )


def compute_metrics(eval_pred) -> dict[str, float]:
    """
    Вычисляет метрики качества классификации.

    Аргументы:
        eval_pred: Кортеж (logits, labels) из модели.

    Возвращаемое значение:
        dict[str, float]: Словарь с метриками accuracy, f1, precision, recall.
    """
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)
    return {
        "accuracy": accuracy_score(labels, predictions),
        "f1": f1_score(labels, predictions, average="binary"),
        "precision": precision_score(labels, predictions, average="binary"),
        "recall": recall_score(labels, predictions, average="binary"),
    }


def is_mostly_cyrillic(text: str, threshold: float = 0.3) -> bool:
    """
    Проверяет, содержит ли текст достаточную долю кириллических символов.

    Аргументы:
        text (str): Исходный текст.
        threshold (float): Минимальная доля кириллических символов.

    Возвращаемое значение:
        bool: True, если доля кириллицы >= threshold.
    """
    if not text:
        return False
    alpha_chars = [c for c in text if c.isalpha()]
    if not alpha_chars:
        return False
    cyrillic = sum(1 for c in alpha_chars if "\u0400" <= c <= "\u04FF")
    return (cyrillic / len(alpha_chars)) >= threshold


def get_model_config(model_name: str) -> dict[str, Any]:
    """
    Возвращает рекомендуемые параметры обучения для модели по её имени.

    Аргументы:
        model_name (str): Имя модели на HuggingFace Hub.

    Возвращаемое значение:
        dict: Словарь с ключами batch_size, max_length, gradient_checkpointing, epochs.
    """
    configs = {
        "cointegrated/rubert-tiny2": {
            "batch_size": 32,
            "max_length": 256,
            "gradient_checkpointing": False,
            "epochs": 7,
        },
        "cointegrated/rubert-tiny": {
            "batch_size": 32,
            "max_length": 256,
            "gradient_checkpointing": False,
            "epochs": 7,
        },
        "deepvk/RuModernBERT-base": {
            "batch_size": 16,
            "max_length": 512,
            "gradient_checkpointing": True,
            "epochs": 5,
        },
        "DeepPavlov/rubert-base-cased": {
            "batch_size": 16,
            "max_length": 256,
            "gradient_checkpointing": False,
            "epochs": 5,
        },
        "DeepPavlov/rubert-base-cased-conversational": {
            "batch_size": 16,
            "max_length": 256,
            "gradient_checkpointing": False,
            "epochs": 5,
        },
    }
    return configs.get(model_name, {
        "batch_size": 16,
        "max_length": 256,
        "gradient_checkpointing": False,
        "epochs": 5,
    })


def benchmark_cpu_inference(
    model,
    tokenizer,
    sample_texts: list[str],
    batch_size: int = 16,
    max_length: int = 256,
) -> dict[str, float]:
    """
    Замеряет latency инференса на CPU для оценки пригодности к развёртыванию.

    Аргументы:
        model: Модель HuggingFace для классификации.
        tokenizer: Токенизатор модели.
        sample_texts (list[str]): Тексты для тестирования.
        batch_size (int): Размер батча для инференса.
        max_length (int): Максимальная длина последовательности.

    Возвращаемое значение:
        dict: Словарь с ключами avg_ms_per_msg, p95_ms_per_msg, throughput_msgs_per_sec.
    """
    model.eval()
    model.to("cpu")
    device = torch.device("cpu")

    latencies = []
    for i in range(0, len(sample_texts), batch_size):
        batch = sample_texts[i : i + batch_size]
        inputs = tokenizer(
            batch,
            padding=True,
            truncation=True,
            max_length=max_length,
            return_tensors="pt",
        ).to(device)

        with torch.no_grad():
            start = time.perf_counter()
            _ = model(**inputs)
            end = time.perf_counter()

        elapsed_ms = (end - start) * 1000
        latencies.extend([elapsed_ms / len(batch)] * len(batch))

    latencies_np = np.array(latencies)
    avg_ms = float(latencies_np.mean())
    p95_ms = float(np.percentile(latencies_np, 95))
    throughput = float(1000.0 / avg_ms) if avg_ms > 0 else 0.0

    return {
        "avg_ms_per_msg": round(avg_ms, 2),
        "p95_ms_per_msg": round(p95_ms, 2),
        "throughput_msgs_per_sec": round(throughput, 2),
    }


def prepare_text_variants(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """
    Подготавливает три варианта текста для дообучения модели.

    Аргументы:
        df (pd.DataFrame): Датафрейм с колонками text_raw, text_normalized,
            text_preprocessed и label.

    Возвращаемое значение:
        dict: Словарь с ключами raw, normalized, preprocessed.
        Каждый элемент — pd.DataFrame с колонками text и label.
    """
    variants = {}

    variants["raw"] = df[["text_raw", "label"]].rename(columns={"text_raw": "text"}).copy()
    variants["raw"]["text"] = variants["raw"]["text"].astype(str)

    if "text_normalized" in df.columns:
        variants["normalized"] = df[["text_normalized", "label"]].rename(
            columns={"text_normalized": "text"}
        ).copy()
        variants["normalized"]["text"] = variants["normalized"]["text"].astype(str)
    else:
        from src.data.preprocessing import normalize_unicode, strip_html

        normalized_texts = df["text_raw"].apply(
            lambda t: strip_html(normalize_unicode(str(t) or ""))
        )
        variants["normalized"] = pd.DataFrame({"text": normalized_texts, "label": df["label"]})

    variants["preprocessed"] = df[["text_preprocessed", "label"]].rename(
        columns={"text_preprocessed": "text"}
    ).copy()
    variants["preprocessed"]["text"] = variants["preprocessed"]["text"].astype(str)

    for key in variants:
        variants[key] = variants[key].dropna(subset=["text"]).reset_index(drop=True)
        variants[key] = variants[key][variants[key]["text"] != "nan"].reset_index(drop=True)

    return variants


def bert_predict_batch(
    messages: list[str],
    classifier,
    threshold: float = 0.5,
    batch_size: int = 16,
) -> list[tuple[int, list[float]]]:
    """
    Батчевое предсказание с помощью модели BERT через pipeline classifier.

    Аргументы:
        messages (list[str]): Список сообщений для анализа.
        classifier: Pipeline классификатор HuggingFace.
        threshold (float): Пороговое значение для предсказания класса 1.
        batch_size (int): Размер батча для инференса.

    Возвращаемое значение:
        list[tuple[int, list[float]]]: Список предсказаний (0 или 1) и вероятностей.
    """
    results = classifier(messages, batch_size=batch_size)
    predictions = []
    for result in results:
        prediction = int(result["label"][-1])
        score = result["score"]
        probabilities = [1 - score, score] if prediction == 1 else [score, 1 - score]
        if probabilities[1] < threshold:
            prediction = 0
        predictions.append((prediction, probabilities))
    return predictions

# Ноутбуки

## Описание

| Папка / файл | Описание |
| --- | --- |
| [`01_data_preparation/`](01_data_preparation/README.md) | Загрузка, очистка, препроцессинг данных и подготовка тестового датасета |
| [`02_data_quality.ipynb`](02_data_quality.ipynb) | Оценка качества датасетов: распределение классов, дрейф, мультиколлинеарность, OOV |
| [`03_classical_baselines/`](03_classical_baselines/README.md) | TF-IDF + числовые признаки, Optuna-тюнинг, оценка, ансамбли (LR, RF, NB, LightGBM, CatBoost) |
| [`04_transformer_models/`](04_transformer_models/README.md) | Дообучение 5 трансформеров (RuBERT-tiny, tiny2, RuModernBERT, RuBERT-base, conversational) и их сравнение |
| [`05_additional_evaluation.ipynb`](05_additional_evaluation.ipynb) | Оценка BERT и классических моделей на внешнем тесте, оптимизация порога, анализ ошибок |
| [`06_hard_negative_mining.ipynb`](06_hard_negative_mining.ipynb) | Поиск и категоризация сложных примеров, на которых BERT ошибается с высокой уверенностью |
| [`07_ablation_study.ipynb`](07_ablation_study.ipynb) | Абляционное исследование: варианты текста, порог, калибровка, анализ ошибок |
| [`08_model_compression.ipynb`](08_model_compression.ipynb) | Сжатие трансформерных моделей: float16 конвертация, ONNX int8 квантизация, дедупликация токенайзеров |

## Порядок работы с ноутбуками

Ноутбуки выполняются последовательно по нумерации:

1. `01_data_preparation/` (01a -> 01b -> 01c -> 01d) — подготовка train и test датасетов
2. `02_data_quality.ipynb` — оценка качества данных
3. `03_classical_baselines/` (03a -> 03b -> 03c -> 03d) — классические модели
4. `04_transformer_models/` (04a–04e независимо, затем 04f) — дообучение и сравнение трансформеров
5. `05_additional_evaluation.ipynb` — оценка на внешнем тесте
6. `06_hard_negative_mining.ipynb` — анализ сложных примеров
7. `07_ablation_study.ipynb` — абляционное исследование
8. `08_model_compression.ipynb` — сжатие моделей для уменьшения размера развёртывания

# СТАНКИН Анти-спам — Исследование

Ветка `research` в репозитории [STANKIN AntiSpam Bot](https://github.com/overklassniy/STANKIN_AntiSpam_Bot).

Содержит Jupyter-ноутбуки, Python-модули и датасеты для обучения и оценки ML-моделей классификации спама в Telegram-чатах.

Обученные модели из этого исследования используются в основной ветке `master`.

## Структура

```
notebooks/
  01_data_preparation/           — загрузка, очистка и препроцессинг данных
  02_data_quality.ipynb          — оценка качества датасетов
  03_classical_baselines/        — классические ML-модели
  04_transformer_models/         — дообучение трансформерных моделей
  05_additional_evaluation.ipynb — оценка на внешнем тесте
  06_hard_negative_mining.ipynb  — анализ сложных примеров
  07_ablation_study.ipynb        — абляционное исследование BERT-моделей
src/                             — Python-модули
data/                            — датасеты (raw, interim, processed)
models/                          — обученные модели и векторизаторы
```

Подробное описание ноутбуков и порядок их выполнения — в [`notebooks/README.md`](notebooks/README.md).

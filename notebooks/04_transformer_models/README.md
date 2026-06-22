# 04. Трансформерные модели

Дообучение pretrained трансформерных моделей для классификации спама.

Все ноутбуки выполняют дообучение на трёх вариантах текста (raw, normalized, preprocessed) с фильтрацией по кириллице (доля > 30%). Используется FocalLoss, FP16, EarlyStopping.

## Ноутбуки

### 04a_rubert_tiny2.ipynb

Дообучение `cointegrated/rubert-tiny2` (29M параметров). Дополнительно применяется TemperatureScaler для калибровки вероятностей.

Оценка на тестовых сообщениях через Hugging Face `pipeline` и замер CPU-инференса.

Модели сохраняются в `models/finetuned_rubert_tiny2_{raw,norm,p}`.

### 04b_rubert_tiny.ipynb

Дообучение `cointegrated/rubert-tiny` (12M параметров, ультра-лёгкая модель).

Модели сохраняются в `models/finetuned_rubert_tiny_{raw,norm,p}`.

### 04c_rumodernbert.ipynb

Дообучение `deepvk/RuModernBERT-base` (150M параметров, ModernBERT архитектура 2025).

Модели сохраняются в `models/finetuned_rumodernbert_{raw,norm,p}`.

### 04d_rubert_base.ipynb

Дообучение `DeepPavlov/rubert-base-cased` (180M параметров, полноразмерный RuBERT).

Модели сохраняются в `models/finetuned_rubert_base_{raw,norm,p}`.

### 04e_rubert_conversational.ipynb

Дообучение `DeepPavlov/rubert-base-cased-conversational` (180M параметров, обучена на чатах и соцсетях).

Модели сохраняются в `models/finetuned_rubert_conv_{raw,norm,p}`.

### 04f_comparison.ipynb

Сравнение всех 5 трансформерных моделей x 3 варианта текста = 15 экспериментов.

Метрики: F1, Precision, Recall, Accuracy, CPU inference latency, размер модели, время обучения.

Финальная рекомендация учитывает trade-off качество/скорость для CPU-only развёртывания. Лучшая модель по результатам сравнения — `rubert-tiny2` на нормализованном тексте (F1=0.9993, 1.87 ms/msg, 113.7 MB).

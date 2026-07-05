# 03. Классические ML-модели

Ноутбуки для подготовки признаков, настройки гиперпараметров, оценки и ансамблирования классических моделей классификации спама.

Модели: Logistic Regression, LinearSVC, SGDClassifier, Naive Bayes, LightGBM.

## Ноутбуки

### 03a_data_and_features.ipynb

Загрузка обучающей и тестовой выборок, подготовка признаков (word TF-IDF, char TF-IDF, 20 числовых признаков) и обучение базовых моделей без настройки гиперпараметров.

Признаки сохраняются в формате `.npz` (scipy.sparse), векторизаторы и базовые модели — в pickle в `data/interim/classic/`.

### 03b_optuna_tuning.ipynb

Поиск гиперпараметров через Optuna для LR, LinearSVC, SGDClassifier, LightGBM. Для Naive Bayes используется grid search по параметру `alpha`. Оптимизация по F1-macro с Stratified K-Fold кросс-валидацией (3 фолда, 10 триалов, MedianPruner).

Результаты сохраняются в `data/interim/classic/optuna_models.pkl`.

### 03c_evaluation_and_analysis.ipynb

Оценка Optuna-моделей на тестовой выборке:

- сравнение с базовыми моделями (classification report, confusion matrix)
- 3-fold Stratified кросс-валидация
- оптимизация порога классификации (Precision при Recall >= 0.90)
- soft voting ансамбль топ-3 моделей
- итоговая таблица сравнения всех моделей (базовые, Optuna, ансамбль)
- анализ ошибок: false positives и false negatives для лучшей модели
- feature importance для LightGBM и Logistic Regression
- демонстрация предсказания на новых сообщениях
- сохранение финальных моделей и векторизаторов в `models/classic/`

# 03. Классические ML-модели

Ноутбуки для подготовки признаков, настройки гиперпараметров, оценки и ансамблирования классических моделей классификации спама.

Модели: Logistic Regression, Random Forest, Naive Bayes, LightGBM, CatBoost.

## Ноутбуки

### 03a_data_and_features.ipynb

Загрузка обучающей и тестовой выборок, подготовка признаков (word TF-IDF, char TF-IDF, 20 числовых признаков) и обучение базовых моделей без настройки гиперпараметров.

Результаты (признаки, векторизаторы, базовые модели) сохраняются в pickle-файлы в `data/interim/`.

### 03b_optuna_tuning.ipynb

Поиск гиперпараметров через Optuna для LR, LightGBM, CatBoost, RF. Для Naive Bayes используется grid search по параметру `alpha`. Оптимизация по F1-macro с Stratified K-Fold кросс-валидацией (3 фолда, 15 триалов).

Результаты сохраняются в `data/interim/optuna_models.pkl`.

### 03c_evaluation.ipynb

Оценка Optuna-моделей на тестовой выборке:

- сравнение с базовыми моделями (classification report, confusion matrix)
- 5-fold Stratified кросс-валидация
- оптимизация порога классификации (Precision при Recall >= 0.90)
- калибровка вероятностей (Isotonic) для топ-3 моделей, оценка Brier score

Результаты сохраняются в `data/interim/evaluation_results.pkl`.

### 03d_ensembles_and_analysis.ipynb

Ансамбли и анализ на основе топ-3 моделей:

1. **Soft Voting** — усреднение предсказанных вероятностей
2. **Stacking** — мета-модель (Logistic Regression) поверх базовых моделей

Дополнительно:

- итоговая таблица сравнения всех моделей (базовые, Optuna, ансамбли)
- анализ ошибок: false positives и false negatives для лучшей модели
- feature importance для LightGBM, CatBoost и Logistic Regression
- демонстрация предсказания на новых сообщениях
- сохранение финальных моделей и векторизаторов в `models/`

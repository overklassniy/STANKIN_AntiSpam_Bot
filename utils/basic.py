# Подгрузка конфигураций из config.json
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Union


def load_config() -> dict:
    """
    Загружает конфигурационные данные из файла config.json.

    Возвращает:
        dict: Словарь с конфигурационными данными.
    """
    with open('config.json', 'r', encoding='UTF-8') as config_file:
        return json.load(config_file)


config = load_config()


# Настройка логирования
def setup_logger() -> logging.Logger:
    """
    Настраивает логирование для вывода в файл и консоль.

    Возвращает:
        logging.Logger: Объект логгера для записи логов.
    """
    logger = logging.getLogger()
    # Если обработчики уже добавлены, не настраиваем логгер заново
    if not logger.handlers:
        os.makedirs(config['LOGS_DIR'], exist_ok=True)
        current_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        log_file_name = f"{config['LOGS_DIR']}/{current_time}.log"

        logger.setLevel(logging.INFO)

        file_handler = logging.FileHandler(log_file_name)
        console_handler = logging.StreamHandler()

        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    return logger


logger = setup_logger()


def plural_form(number: int, singular: str, plural_genitive: str, plural_nominative: str) -> str:
    """
    Возвращает форму слова в зависимости от числа перед ним.

    Параметры:
        number (int): Число перед словом.
        singular (str): Форма слова при числе, заканчивающемся на 1.
        plural_genitive (str): Форма слова при числе, заканчивающемся на 2-4 или на 11-19.
        plural_nominative (str): Форма слова при числе, заканчивающемся на 2-4, кроме случаев, когда число заканчивается на 12-14.

    Возвращает:
        str: Правильная форма слова в зависимости от числа.
    """
    if 11 <= number % 100 <= 19:
        return plural_genitive
    elif number % 10 == 1:
        return singular
    elif 2 <= number % 10 <= 4:
        return plural_nominative
    else:
        return plural_genitive


# Функции для работы с файлами JSON
def load_json_file(file_path: str, default_value: Union[dict, list]) -> Union[dict, list]:
    """
    Загружает данные из JSON файла. Если файл не существует, возвращает значение по умолчанию.

    Параметры:
        file_path (str): Путь к JSON файлу.
        default_value (dict | list): Значение по умолчанию, если файл не найден.

    Возвращает:
        dict | list: Данные, загруженные из JSON файла, или значение по умолчанию.
    """
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return json.load(f)
    return default_value


def save_json_file(file_path: str, data: Union[dict, list]) -> None:
    """
    Сохраняет данные в JSON файл.

    Параметры:
        file_path (str): Путь к JSON файлу.
        data (dict | list): Данные для сохранения.
    """
    # Получаем директорию из пути к файлу
    directory = os.path.dirname(file_path)

    # Проверяем, существует ли директория, и создаем её, если нет
    if not os.path.exists(directory):
        os.makedirs(directory)

    # Сохраняем данные в JSON файл
    with open(file_path, 'w') as f:
        json.dump(data, f)


def get_pkl_files(directory) -> Union[list, dict]:
    """
    Возвращает список всех файлов с расширением .pkl из указанной папки.

    Параметры:
        directory (str): Путь к папке, в которой нужно искать файлы.

    Возвращает:
        list | dict: Список названий файлов с расширением .pkl или сообщение об ошибке.
    """
    try:
        # Проверяем, существует ли директория
        if not os.path.isdir(directory):
            return {"error": f"Папка '{directory}' не существует."}

        # Получаем список всех файлов с расширением .pkl
        pkl_files = [file for file in os.listdir(directory) if file.endswith('.pkl')]
        return pkl_files

    except Exception as e:
        return {"error": str(e)}


def add_hours_get_timestamp(n: int) -> float:
    if n == 999:
        return 4102455600  # 2100 год
    new_time = datetime.now() + timedelta(hours=n)
    return new_time.timestamp()
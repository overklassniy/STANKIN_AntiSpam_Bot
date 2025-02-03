import json
import logging
import os
from datetime import datetime, timedelta
from typing import Union


# Подгрузка конфигураций из config.json
def load_config() -> dict:
    """
    Загружает конфигурационные данные из файла config.json.

    Возвращает:
        dict: Словарь с конфигурационными данными.
    """
    with open('config.json', 'r', encoding='UTF-8') as config_file:
        return json.load(config_file)


config = load_config()


def setup_logger() -> logging.Logger:
    """
    Настраивает логирование для вывода в файл и консоль.

    Возвращает:
        logging.Logger: Объект логгера для записи логов.
    """
    logger_obj = logging.getLogger()
    # Если обработчики уже добавлены, не настраиваем логгер заново
    if not logger_obj.handlers:
        os.makedirs(config['LOGS_DIR'], exist_ok=True)
        current_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        log_file_name = f"{config['LOGS_DIR']}/{current_time}.log"
        logger_obj.setLevel(logging.INFO)

        # Логирование в файл с явным указанием кодировки UTF-8
        file_handler = logging.FileHandler(log_file_name, encoding="utf-8")

        # Логирование в консоль с поддержкой UTF-8
        console_handler = logging.StreamHandler()
        console_handler.stream.reconfigure(encoding="utf-8")

        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        logger_obj.addHandler(file_handler)
        logger_obj.addHandler(console_handler)
        logger_obj.info("Логгер успешно настроен. Логи записываются в файл: %s", log_file_name)
    else:
        logger_obj.info("Логгер уже настроен ранее.")

    return logger_obj


logger = setup_logger()


def plural_form(number: int, singular: str, plural_genitive: str, plural_nominative: str) -> str:
    """
    Возвращает форму слова в зависимости от числа перед ним.

    Аргументы:
        number (int): Число перед словом.
        singular (str): Форма слова при числе, заканчивающемся на 1.
        plural_genitive (str): Форма слова для чисел от 11 до 19 и для большинства остальных случаев.
        plural_nominative (str): Форма слова при числах, оканчивающихся на 2-4, кроме 12-14.

    Возвращает:
        str: Правильная форма слова в зависимости от числа.
    """
    logger.debug("Вычисление формы для числа: %s", number)
    if 11 <= number % 100 <= 19:
        form = plural_genitive
    elif number % 10 == 1:
        form = singular
    elif 2 <= number % 10 <= 4:
        form = plural_nominative
    else:
        form = plural_genitive
    logger.debug("Для числа %s выбрана форма: %s", number, form)
    return form


def load_json_file(file_path: str, default_value: Union[dict, list]) -> Union[dict, list]:
    """
    Загружает данные из JSON файла. Если файл не существует, возвращает значение по умолчанию.

    Аргументы:
        file_path (str): Путь к JSON файлу.
        default_value (dict | list): Значение по умолчанию, если файл не найден.

    Возвращает:
        dict | list: Данные, загруженные из JSON файла, или значение по умолчанию.
    """
    logger.info("Загрузка JSON файла: %s", file_path)
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='UTF-8') as f:
                data = json.load(f)
                logger.info("Файл %s успешно загружен.", file_path)
                return data
        except Exception as e:
            logger.error("Ошибка при загрузке файла %s: %s", file_path, e)
            return default_value
    else:
        logger.warning("Файл %s не найден. Используется значение по умолчанию.", file_path)
        return default_value


def save_json_file(file_path: str, data: Union[dict, list]) -> None:
    """
    Сохраняет данные в JSON файл.

    Аргументы:
        file_path (str): Путь к JSON файлу.
        data (dict | list): Данные для сохранения.
    """
    logger.info("Сохранение данных в JSON файл: %s", file_path)
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        try:
            os.makedirs(directory)
            logger.info("Создана директория: %s", directory)
        except Exception as e:
            logger.error("Ошибка при создании директории %s: %s", directory, e)
            return
    try:
        with open(file_path, 'w', encoding='UTF-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        logger.info("Данные успешно сохранены в файл: %s", file_path)
    except Exception as e:
        logger.error("Ошибка при сохранении файла %s: %s", file_path, e)


def get_pkl_files(directory: str) -> Union[list, dict]:
    """
    Возвращает список всех файлов с расширением .pkl из указанной папки.

    Аргументы:
        directory (str): Путь к папке, в которой нужно искать файлы.

    Возвращает:
        list | dict: Список названий файлов с расширением .pkl или сообщение об ошибке.
    """
    logger.info("Поиск файлов с расширением .pkl в директории: %s", directory)
    try:
        if not os.path.isdir(directory):
            error_message = f"Папка '{directory}' не существует."
            logger.error(error_message)
            return {"error": error_message}

        pkl_files = [file for file in os.listdir(directory) if file.endswith('.pkl')]
        logger.info("Найдено %s файлов с расширением .pkl в директории %s.", len(pkl_files), directory)
        return pkl_files
    except Exception as e:
        logger.error("Ошибка при поиске файлов в директории %s: %s", directory, e)
        return {"error": str(e)}


def add_hours_get_timestamp(n: int) -> float:
    """
    Добавляет указанное количество часов к текущему времени и возвращает метку времени.
    При значении n равном 999 возвращает фиксированное значение (год 2100).

    Аргументы:
        n (int): Количество часов для добавления.

    Возвращает:
        float: Метка времени после добавления часов.
    """
    if n == 999:
        logger.info("Возвращается фиксированное время для значения n=999.")
        return 4102455600  # 2100 год
    new_time = datetime.now() + timedelta(hours=n)
    timestamp = new_time.timestamp()
    logger.info("Время обновлено: добавлено %s часов, новая метка времени: %s", n, timestamp)
    return timestamp

from utils.basic import logger


def prepare_fields(config: dict) -> list:
    """
    Подготавливает список полей для шаблона.

    Аргументы:
        config (dict): Конфигурация с параметрами.

    Возвращает:
        list: Список словарей, где каждый словарь содержит:
              'name': имя поля (ключ из конфигурации),
              'value': значение параметра,
              'type': тип input ('checkbox' для булевых, 'number' для чисел, 'text' для остальных).
    """
    logger.info("Начало подготовки полей для шаблона из конфигурации.")
    fields = []
    for key, value in config.items():
        if isinstance(value, bool):
            field_type = 'checkbox'
        elif isinstance(value, (int, float)):
            field_type = 'number'
        else:
            field_type = 'text'
        fields.append({
            'name': key,
            'value': value,
            'type': field_type
        })
        logger.debug("Добавлено поле: %s, значение: %s, тип: %s", key, value, field_type)
    logger.info("Подготовка полей завершена. Всего полей: %s", len(fields))
    return fields

def prepare_fields(config):
    """
    Подготавливает список полей для шаблона.
    Каждое поле представлено в виде словаря с ключами:
    - name: имя поля (ключ из конфига)
    - value: значение параметра
    - type: тип input ('checkbox' для булевых, 'number' для чисел, 'text' для остальных)
    """
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
    return fields

""""
JSON Schema Draft 7 и схемы для валидации данных
Подробнее о JSON Schema на https://json-schema.org/understanding-json-schema/index.html

"""
from typing import Dict, List, Any, Optional, Union


def _const(value: Any) -> Dict[str, Any]:
    """
    :param value: значение

    Постоянное значение JSON Schema Draft 7
    """

    return {
        "const": value
    }


def _enum(*args: Any) -> Dict[str, Any]:
    """
    :param *args:
    :param args: Члены перечисления

    Перечисление JSON Schema Draft 7
    """
    return {
        "enum": list(args)
    }


def _null():
    """
    Тип null JSON Schema Draft 7
    """

    return {
        "type": "null"
    }


def _nullable(constraint: Dict[str, str]) -> Dict[str, str]:
    """

    :param constraint: ограничение, к которому применяется модификатор
    :return: новое ограничение

    Модификатор типа, добавляющий `null`, как возможный вариант типа
    """

    type_ = constraint.get('type')
    if type_ is None:
        new_type = "null"
    elif isinstance(type_, str):
        new_type = [type_, "null"]
    else:
        new_type = [*type_, "null"]

    constraint.update({'type': new_type})
    return constraint


def _bool() -> Dict[str, str]:
    """
    Логический тип JSON Schema Draft 7
    """

    return {
        "type": "boolean"
    }


def _str(
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        pattern: Optional[str] = None
) -> Dict[str, Any]:
    """
    :param min_length: минимальная длина строки
    :param max_length: максимальная длина строки
    :param pattern: паттерн, которому должна соответствовать строка

    Строка JSON Schema Draft 7
    """

    str_constraint = {
        "type": "string",
    }

    optional_constraints = {
        "minLength": min_length,
        "maxLength": max_length,
        "pattern": pattern
    }

    for name, val in optional_constraints.items():
        if val is not None:
            str_constraint[name] = val

    return str_constraint


def _int(
        minimum: Optional[int] = None,
        exclusive_minimum: Optional[bool] = None,
        maximum: Optional[int] = None,
        exclusive_maximum: Optional[bool] = None,
        multiple_of: Optional[int] = None
) -> Dict[str, Any]:
    """
    :param minimum: Минимальное значение, допустимое для числа
    :param exclusive_minimum: Исключительный ли минимум
    :param maximum: Максимальное значение, допустимое для числа
    :param exclusive_maximum: Исключительный ли максимум
    :param multiple_of: если передано, число должно делиться на этот параметр

    Целочисленный тип тип JSON Schema Draft 7

    """

    int_constrain = {
        "type": "integer"
    }
    if minimum is not None:
        int_constrain.update(
            {
                "minimum": minimum
            }
        )
        if exclusive_minimum is not None:
            int_constrain.update(
                {
                    "exclusiveMinimum": exclusive_minimum
                }
            )
    if maximum is not None:
        int_constrain.update(
            {
                "maximum": maximum
            }
        )
        if exclusive_maximum is not None:
            int_constrain.update(
                {
                    "exclusiveMaximum": exclusive_maximum
                }
            )
    if multiple_of is not None:
        int_constrain.update(
            {
                "multipleOf": multiple_of
            }
        )
    return int_constrain


def _number(
        minimum: Optional[float] = None,
        exclusive_minimum: Optional[bool] = None,
        maximum: Optional[float] = None,
        exclusive_maximum: Optional[bool] = None,
        multiple_of: Optional[float] = None
) -> Dict[str, Any]:
    """
    :param minimum: Минимальное значение, допустимое для числа
    :param exclusive_minimum: Исключительный ли минимум
    :param maximum: Максимальное значение, допустимое для числа
    :param exclusive_maximum: Исключительный ли максимум
    :param multiple_of: если передано, число должно делиться на этот параметр

    Числовой тип тип JSON Schema Draft 7

    """

    number_constrain = {
        "type": "number"
    }
    if minimum is not None:
        number_constrain.update(
            {
                "minimum": minimum
            }
        )
        if exclusive_minimum is not None:
            number_constrain.update(
                {
                    "exclusiveMinimum": exclusive_minimum
                }
            )
    if maximum is not None:
        number_constrain.update(
            {
                "maximum": maximum
            }
        )
        if exclusive_maximum is not None:
            number_constrain.update(
                {
                    "exclusiveMaximum": exclusive_maximum
                }
            )
    if multiple_of is not None:
        number_constrain.update(
            {
                "multipleOf": multiple_of
            }
        )
    return number_constrain


def _array(
        items: Union[Dict, List[Dict], None] = None,
        min_length: int = 0,
        max_length: Optional[int] = None,
        unique: bool = False,
        additional_items: bool = False
) -> Dict[str, Any]:
    """
    :param items: Описание элементов списка
    :param min_length: минимальная длина списка
    :param max_length: максимальная длина списка
    :param unique: должен ли список содержать только уникальные элементы
    :param additional_items: разрешены ли дополнительные элементы в списке

    Списочный тип JSON Schema Draft 7

    """

    array_constraint = {
        "type": "array",
        "minItems": min_length,
        "uniqueItems": unique,
        "additionalItems": additional_items
    }

    optional_constraints = {
        'items': items,
        'maxItems': max_length
    }

    for name, val in optional_constraints.items():
        if val is not None:
            array_constraint[name] = val

    return array_constraint


def _obj(
        required_properties: Optional[Dict[str, Any]] = None,
        optional_properties: Optional[Dict[str, Any]] = None,
        additional_property: Union[bool, Dict[str, Any]] = False,
        min_properties: Optional[int] = None,
        max_properties: Optional[int] = None,
        property_names: Optional[Dict[str, Dict[str, Any]]] = None,
        pattern_properties: Optional[Dict[str, Dict[str, Any]]] = None,
        dependencies: Optional[Dict[str, Dict[str, Any]]] = None
) -> Dict[str, Dict[str, Any]]:
    """
    :param required_properties: обязательные свойства
    :param optional_properties: необязательные свойства
    :param additional_property: спецификатор дополнительных полей
    :param min_properties: минимальное количество свойств у объекта
    :param max_properties: максимальное количество свойств у объекта
    :param property_names: спецификатор для имён свойств
    :param pattern_properties: спецификатор правил, зависимых от регулярного выражения.

    Объектный тип тип JSON Schema Draft 7
    """

    properties = dict()
    if required_properties is not None:
        properties = required_properties.copy()
    if optional_properties is not None:
        properties.update(optional_properties)

    obj_constraint = {
        "type": "object",
        "properties": properties,
        "required": list(required_properties.keys()) if required_properties is not None else [],
        "additionalProperties": additional_property
    }

    optional_constraints = {
        'minProperties': min_properties,
        'maxProperties': max_properties,
        'propertyNames': property_names,
        'patternProperties': pattern_properties,
        'dependencies': dependencies
    }

    for name, val in optional_constraints.items():
        if val is not None:
            obj_constraint[name] = val

    return obj_constraint


# Project constraint helpers

def _file(mimetype: Union[str, List[str]] = '*/*'):
    """

    :param mimetype: тип файла. См. mimetype
    :return: Файловый тип Custom JSON Schema

    Возвращает описания файла для JSON Schema - подобной схеме специфичной для данного проекта.
    Должен использоваться только для схем, используемых для проверки файлов
    """
    return {
        'mimetype': mimetype
    }


def from_sqlalchemy_column(column, extra: Optional[Dict[str, Any]]):

    orig_name = column.name
    descriptor = None

    if column.type.python_type == str:
        descriptor = _str(
            max_length=column.type.length
        )
    elif column.type.python_type == int:
        descriptor = _int()

    elif column.type.python_type == bool:
        descriptor = _bool()

    if descriptor is not None and column.nullable:
        descriptor = _nullable(descriptor)

    if descriptor is None:
        descriptor = {}

    if extra is not None and len(extra) > 0:
        descriptor.update(extra)

    return orig_name, descriptor


def _integer_as_string() -> Dict[str, Any]:
    """
    Целочисленный тип, переданный строкой

    """

    return _str(
        pattern='^\\d+$'
    )


def _integer_as_string_or_empty() -> Dict[str, Any]:
    """
    Целочисленный тип, переданный строкой (Возможно пустой)

    """

    return _str(
        pattern='^\\d*$'
    )


def _email():
    return _str(
        pattern='.+@.+\\..+'
    )


def _tel():
    return _str(
        pattern=r'\d{0,16}'
    )


def siw_password():
    return _obj(
        required_properties={
            'email': _str(),
            'password': _str()
        }
    )


def renew_token():
    return _obj(
        required_properties={
            'refresh': _str(pattern=r'[\da-f]{64}')
        }
    )


def text():
    return _obj(
        required_properties={
            'text': _str()
        }
    )


def editing_device():
    return _obj(
        required_properties={
            'device': _str(),
            'enable_notifications': _bool()
        },
        optional_properties={
            'has_subscription': _bool()
        }
    )


def editing_bool_mark():
    return _obj(
        required_properties={
            'value': _bool()
        }
    )


def email_body():
    return _obj(
        required_properties={
            'email': _email()
        }
    )


def edit_profile_avatar():
    return _obj(
        required_properties={
            'image': _file('image/*')
        }
    )


def upload_attachment():
    return _obj(
        required_properties={
            'file': _file()
        }
    )


def edit_profile():
    return _obj(
        optional_properties={
            'height': _int(),
            'actual_weight': _int(),
            'target_weight': _int(),
            'name': _str(),
            'last_name': _str(),
            'birthday': _int(),
            'country': _str(),
            'city': _str(),
            'unit_system': _enum(0, 1),
            'email': _str(),
            'gender': _enum(0, 1)
        }
    )


def edit_workout_days():
    return _obj(
        required_properties={
            'days': _array(
                items=_int(minimum=0, maximum=6)
            )
        }
    )


def edit_workout_time():
    return _obj(
        required_properties={
            'time': _array(
                items=_int(minimum=0, maximum=86399)
            )
        }
    )


def inform():
    return _obj(
        optional_properties={
            'timestamp': _int()
        }
    )


def with_tel():
    return _obj(
        required_properties={
            'tel': _tel(),
        }
    )


def siw_tel():
    return _obj(
        required_properties={
            'tel': _tel(),
            'code': _str(pattern=r'\d{4}'),
        }
    )


def create_room():
    return _obj(
        required_properties={
            'name': _str(),
            'address': _str(),
            'description': _nullable(_str()),
            'price': _int(),
            'humans_count': _int(),
            'number': _int(),
            'area': _int(),
            'amenities': _array(items=_int()),
            'attachments': _array(items=_int()),
        }
    )


def rent_room():
    return _obj(
        required_properties={
            'comment': _nullable(_str()),
            'start_at': _int(),
            'end_at': _int(),
            'renters': _array(
                items=_obj(
                    required_properties={
                        'grown_ups_count': _int(),
                        'children_count': _int()
                    }
                )
            )
        },
        optional_properties={
            'first_name': _nullable(_str()),
            'last_name': _nullable(_str()),
            'tel': _str()
        }
    )


def edit_rent():
    return _obj(
        required_properties={
            'verified': _bool()
        }
    )
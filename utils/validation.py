"""
Модуль для валидации данных
"""
from copy import copy
from functools import wraps
from typing import Dict, Any, Union, Iterable, List, Optional
from urllib import parse

import jsonschema
from flask import request, g
from jsonschema import ValidationError
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import abort, HTTPException


def _validate_mimetype(validator, value, instance, schema):
    if isinstance(value, str):
        expected_mimetype = value.split('/')
        real_mimetype = instance.mimetype.split('/')
        if (expected_mimetype[0] != '*' and expected_mimetype[0] != real_mimetype[0]) \
                or (expected_mimetype[1] != '*' and expected_mimetype[1] != real_mimetype[1]):
            return [
                ValidationError('Unexpected mimetype')
            ]
    else:
        is_valid = False
        real_mimetype = instance.mimetype.split('/')
        for item in value:
            expected_mimetype = item.split('/')
            if (expected_mimetype[0] == '* ' or expected_mimetype[0] == real_mimetype[0]) \
                    and (expected_mimetype[1] == '*' or expected_mimetype[1] == real_mimetype[1]):
                is_valid = True
        if not is_valid:
            return [
                ValidationError('Unexpected mimetype')
            ]


def _create_json_path(path: Iterable, root: str = '$') -> str:
    """
    :param path: элементы пути
    :param root: префикс пути
    :return: JSON Path

    Формирует строку представляющую JSON Path из отдельных элементов пути
    """

    json_path = root
    for point in path:
        if type(point) == int:
            json_path += f'[{point}]'
        else:
            json_path += f'.{point}'
    return json_path


def _get_json(r):
    try:
        data = r.get_json()
    except HTTPException:
        data = None
    return data


def _get_form(r):
    form = {}

    for field in r.files.keys():
        files = r.files.getlist(field)
        if len(files) == 1:
            form[field] = files[0]
        else:
            form[field] = files

    form.update(r.form)

    return form


def validate(schema: dict, instance: Union[dict, list], root: str = '$') -> List[dict]:
    """
    :param schema: JSON Schema Draft 7 (https://json-schema.org/draft/2019-09/release-notes.html)
    :param instance: проверяемые данные
    :param root: префикс JSON Path
    :return: Список ошибок валидации

    Проверяет текстовые на соответствия схеме по спецификации JSON Schema Draft 7 и бинарные данные на соответствие заявленому типу
    """

    print(instance)

    v = jsonschema.Draft7Validator(schema)
    file_checker = v.TYPE_CHECKER.redefine('file', lambda _, inst: isinstance(inst, FileStorage))
    v = jsonschema.validators.extend(
        validator=v,
        validators={
            'mimetype': _validate_mimetype
        },
        type_checker=file_checker
    )(schema)
    errors = sorted(v.iter_errors(instance), key=lambda e: e.path)
    modified_errors = []
    for error in errors:

        schema_path = error.absolute_schema_path

        path_to_value = _create_json_path(list(error.absolute_path)[:-1], root=root)
        if schema_path[0] == 'additionalProperties':
            for field in error.message[40:-17].split(','):
                modified_error = copy(error)
                setattr(modified_error, 'custom_source', field.strip(' ').strip('\''))
                setattr(modified_error, 'custom_path', _create_json_path(list(error.absolute_path), root=root))
                modified_errors.append(modified_error)

        elif schema_path[-1] == 'required':
            modified_error = copy(error)
            setattr(modified_error, 'custom_source', error.args[0][1:-24])
            setattr(modified_error, 'custom_path', path_to_value)
            modified_errors.append(modified_error)

        elif schema_path[-1] == 'type':
            modified_error = copy(error)
            setattr(modified_error, 'custom_source', schema_path[-2])
            setattr(modified_error, 'custom_path', path_to_value)
            modified_errors.append(modified_error)

        elif len(schema_path) > 2:
            modified_error = copy(error)
            setattr(modified_error, 'custom_source', schema_path[-2])
            setattr(modified_error, 'custom_path', _create_json_path(list(error.absolute_path)[:-1], root=root))
            modified_errors.append(modified_error)

        else:
            modified_error = copy(error)
            setattr(modified_error, 'custom_source', schema_path[-1])
            setattr(modified_error, 'custom_path', error.validator_value)
            modified_errors.append(modified_error)

    return modified_errors


class NotAllowedContentTypeError(Exception):
    """
    Ошибка неподдерживаемого типа содержимого
    """

    pass


class NoBodyError(Exception):
    """
    Ошибка отсутствующего тела запроса
    """
    pass


class InvalidRequestError(Exception):
    """
    Ошибка невалидного запроса
    """

    def __init__(self, errors: List[Exception]):
        super(InvalidRequestError, self).__init__()
        self.errors = errors


class Section:
    """Отдельный раздел http-запроса"""

    def __init__(self, raw):
        self.raw = raw
        self._fields = {}

    def __getitem__(self, item):
        return self._fields[item]

    def __getattr__(self, item):
        return self._fields[item]

    def __contains__(self, item):
        return item in self._fields

    def get(self, key, default=None):
        return self._fields.get(key, default)

    def get_all(self):
        return self._fields

    def add_field(self, name: str, value: Any) -> None:
        """
        :param name: имя поля
        :param value: значение поля

        Добавить поле в раздел
        """
        self._fields[name] = value


class ParsedRequest:
    """
    Класс, представляющий разобранный http-запрос
    """

    def __init__(
            self,
            url: Optional[Section] = None,
            query: Optional[Section] = None,
            body: Optional[Section] = None,

    ):
        self.url = url
        self.query = query
        self.body = body


class RequestValidator:
    """
    Валидатор http-запросов
    """

    def __init__(self):

        self._system_parsers = {
            'application/json': _get_json,
            'multipart/form-data': _get_form
        }

        self.parsers = {}

    def validate(
            self,
            allowed_content_types: Optional[List[str]] = None,
            url_params: Optional[Dict[str, Any]] = None,
            query_params: Optional[Dict[str, Any]] = None,
            body_fields: Optional[Dict[str, Any]] = None
    ):

        """
        :param allowed_content_types: Поддерживаемые mimetype'ы запроса. Обратите внимание, что предварительно должен быть зарегистрирован соответствующий парсер
        :param url_params: Параметры пути в url
        :param query_params: Параметры запроса в url
        :param body_fields: Параметры тела запроса

        Декоратор для проверки http-запроса. Добавляет в g объект, представляющий разобранный http-запрос

        """

        if (body_fields is None) != (allowed_content_types is None):
            raise ValueError('Incompatible set of arguments')

        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):

                errors = []

                if url_params is not None:
                    if len(validate(url_params, kwargs, root='$.url_params')) > 0:
                        abort(404)

                if query_params is not None:
                    errors += validate(query_params, request.args, root='$.query_params')

                preparsed_body = None

                if allowed_content_types is not None:

                    content_type_not_allowed = True
                    real_content_type = request.content_type

                    if real_content_type is not None:

                        semicolon_position = real_content_type.find(';')
                        if semicolon_position != -1:
                            real_content_type = real_content_type[:semicolon_position]

                        real_content_type_parts = real_content_type.split('/')

                        for allowed_content_type in allowed_content_types:
                            allowed_content_type_parts = allowed_content_type.split('/')

                            if (
                                    allowed_content_type_parts[0] == '*'
                                    or allowed_content_type_parts[0] == real_content_type_parts[0]
                            ) and (
                                    allowed_content_type_parts[1] == '*'
                                    or allowed_content_type_parts[1] == real_content_type_parts[1]
                            ):

                                content_type_not_allowed = False
                                for parsable_content_type, parser in self._system_parsers.items():
                                    parsable_content_type_parts = parsable_content_type.split('/')

                                    if (
                                            parsable_content_type_parts[0] == '*'
                                            or parsable_content_type_parts[0] == real_content_type_parts[0]

                                    ) and (
                                            parsable_content_type_parts[1] == '*'
                                            or parsable_content_type_parts[1] == real_content_type_parts[1]
                                    ):
                                        preparsed_body = parser(request)

                                        break
                                for parsable_content_type, parser in self.parsers.items():
                                    parsable_content_type_parts = parsable_content_type.split('/')
                                    if (
                                            parsable_content_type_parts[0] == '*'
                                            or parsable_content_type_parts[0] == real_content_type_parts[0]

                                    ) and (
                                            parsable_content_type_parts[1] == '*'
                                            or parsable_content_type_parts[1] == real_content_type_parts[1]
                                    ):
                                        preparsed_body = parser(request.data)
                                        break

                                break

                    if content_type_not_allowed:
                        errors.append(NotAllowedContentTypeError())
                    else:
                        if body_fields is not None:
                            if preparsed_body is None:
                                errors.append(NoBodyError())
                            else:
                                errors += validate(body_fields, preparsed_body, root='$.body_fields')

                if len(errors) > 0:
                    raise InvalidRequestError(errors=errors)

                parsed_url_params = Section(raw=request.path)

                for name, value in kwargs.items():
                    parsed_url_params.add_field(name, value)

                parsed_query_params = Section(raw=parse.urlencode(request.args))

                for name, value in request.args.items():
                    parsed_query_params.add_field(name, value)

                parsed_body = None

                if preparsed_body is not None:
                    parsed_body = Section(raw=request.get_data())
                    for name, value in preparsed_body.items():
                        parsed_body.add_field(name, value)

                g.received = ParsedRequest(
                    url=parsed_url_params,
                    query=parsed_query_params,
                    body=parsed_body
                )

                g.request_schema = {
                    'allowed_content_types': allowed_content_types,
                    'url': url_params,
                    'query': query_params,
                    'body': body_fields
                }

                return f(*args, **kwargs)

            return decorated_function

        return decorator

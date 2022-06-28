"""
Вспомогательные функции для создания сложных структур данных
"""
import os
from http import HTTPStatus
import random
from typing import Optional, Any, Dict, Tuple, Union

from flask_sqlalchemy import Pagination
# from werkzeug.exceptions import abort
from werkzeug.datastructures import FileStorage

from utils.map import Map


def make_response(
        message: Optional[str] = None,
        data: Any = None,
        status: int = 200,
        errors: list = None,
        paginator: Optional[Union[Pagination, Map]] = None,
        strict: bool = False,
        extra_headers: Optional[Dict[str, str]] = None,
        description: str = ""
) -> Tuple[Union[dict, list, str], str, Dict[str, str]]:
    """
    Формирует ответ сервера

    :param message: кастомное сообщение для статуса ответа
    :param data: данные для формирования тела ответа
    :param status: статус ответа
    :param errors: список ошибок для ответа
    :param paginator: объект пагинации
    :param strict: режим формирования ответа.
    :param extra_headers: дополнительные заголовки
    :param description: Описания результата
    :return: Ответ сервера в формате (Тело, Статус, Дополнительные заголовки)
    """

    real_extra_headers = {} if extra_headers is None else extra_headers
    extra_headers_valid = True

    # Получаем список ошибок
    error_list = [] if errors is None else errors

    # Работаем с статусом ответа
    real_status = status
    status_valid = True

    if strict and not (real_extra_headers is None and isinstance(real_extra_headers, dict)):
        real_status = 500
        extra_headers_valid = False
        real_extra_headers = {}

    # Статус должен быть числовым
    if type(status) != int:
        status_valid = False
        if strict:
            real_status = 500
    # и находится в диапазоне от 100 включительно до 600 исключительно
    elif status >= 600 or status < 100:
        status_valid = False
        if strict:
            real_status = 500

    # Если список ошибок не пустой,то в строгом режиме статус должен быть либо 4xx, либо 5xx.
    if strict and len(error_list) > 0 and (type(status) != int or status // 100 in [4, 5]):
        real_status = 500

    # Формируем сообщение об ответе
    real_message = message
    # Если не задано ответное сообщение сервера
    if message is None:
        # и код ответа стандартен,
        if real_status in HTTPStatus._value2member_map_:
            # получаем стандартное ответное сообщение и нормализуем его
            real_message = HTTPStatus(real_status).name.replace('_', ' ').capitalize()
        # иначе
        else:
            # если код ответа валидный или исправлен строгим режимом
            if status_valid or strict:
                # то получаем обобщенное сообщение по классу статуса
                real_message = HTTPStatus(real_status // 100 * 100).name.replace('_', ' ').capitalize()
            else:
                # или выставляем дефолтное
                real_message = 'Unknown'

    # Код ответа 204 в строгом режиме игнорирует тело ответа
    if strict and real_status == 204:
        return '', f'{real_status} {real_message}', {}
    else:

        # if real_status // 100 in [4, 5]:
        #     abort(real_status)

        # Если полезная нагрузка не список, словарь или None,
        if data is not None and not isinstance(data, (list, dict,)):
            # то используем строковое представление полезной нагрузки
            return str(data), f'{real_status} {real_message}', {}

        # иначе формируем json

        # мета данные
        meta = {
            'pagination': None
        }
        # если передан пагинатор,
        if paginator is not None:
            # то формируем метаданные для пагинации
            meta['pagination'] = {
                'page': paginator.page,
                'total': paginator.pages,
                'has_prev': paginator.has_prev,
                'has_next': paginator.has_next
            }

        # Формируем ответ

        return (
                   {
                       'message': real_message,
                       'meta': meta,
                       'data': data,
                       'errors': error_list,
                       'description': description
                   }
               ), f'{real_status} {real_message}', real_extra_headers


def save_file(file: FileStorage, static_folder: str, to_dir: str) -> str:
    length = 12
    file_name = hex(random.getrandbits(4 * length))[2:].rjust(length, '0') \
                + os.path.splitext(file.filename)[-1]

    saving_dir = os.path.join(static_folder, to_dir)

    if not os.path.isdir(saving_dir):
        os.makedirs(saving_dir)

    saving_path = os.path.join(saving_dir, file_name)

    file.save(saving_path)

    file_path = os.path.join(to_dir, file_name)

    return file_path



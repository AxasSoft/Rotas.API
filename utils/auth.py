"""
Модуль для работы с аутентификацией и авторизацией
"""

import random
from datetime import datetime
from functools import wraps
import re
from typing import Optional, List, Union

from flask import request, g

from app.models import Token, UserType
from utils.helpers import make_response


def gen_token(length: int = 64, fixed_prefix: str = '00') -> str:
    """
    :param length: длина токена
    :param fixed_prefix: фиксированный префикс
    :return: сгенерированный токен

    Генерирует случайный токен. Уникальность не гарантируется
    """
    rnd_len = length - len(fixed_prefix)
    return fixed_prefix + hex(random.getrandbits(rnd_len * 4))[2:].rjust(rnd_len, '0')


def auth(
        require: bool = True,
        user_types: Optional[List[Optional[UserType]]] = None,
        is_admin: Optional[bool] = None,
):
    """

    Формирует декоратор для авторизации, основанной на токенах доступа
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = None
            token_pair = None
            if 'Authorization' not in request.headers and require:
                return make_response(
                    errors=[
                        {
                            'code': 1,
                            'message': 'Header "Authorization" not provided',
                            'source': 'headers',
                            'path': '$',
                            'additional': None
                        }
                    ],
                    status=401,
                    description='Заголовок авторизации не предоставлен'
                )
            if 'Authorization' in request.headers:
                regexp = r"^Token [\da-f]{64}$"
                if re.match(regexp, request.headers['Authorization']) is None:
                    return make_response(
                        errors=[
                            {
                                'code': 2,
                                'message': 'Invalid value of header "Authorization"',
                                'source': 'headers',
                                'path': '$',
                                'additional': {
                                    'regexp': regexp
                                }
                            }
                        ],
                        status=401,
                        description='Невалидный заголовок авторизации'
                    )
                token_value = request.headers['Authorization'][6:]
                token: Optional[Token] = Token.query.filter(
                    Token.value == token_value,
                    Token.as_access != None
                ).first()

                if token is None:
                    return make_response(
                        errors=[
                            {
                                'code': 3,
                                'message': 'Incorrect value of header "Authorization"',
                                'source': 'headers',
                                'path': '$',
                                'additional': request.headers['Authorization']
                            }
                        ],
                        status=401,
                        description='Невалидное значение заголовка авторизации'
                    )

                # if token.expires_at < datetime.utcnow():
                #     return make_response(
                #         errors=[
                #             {
                #                 'code': 4,
                #                 'message': 'Token Expired',
                #                 'source': 'headers',
                #                 'path': '$',
                #                 'additional': None
                #             }
                #         ],
                #         status=401,
                #         description='Время жизни авторизационного токена истекло'
                #     )

                token_pair = token.as_access
                user = token_pair.user

                g.user = user

                user_type = user.user_type.value if user.user_type is not None else None

                if (is_admin is not None and is_admin != user.is_admin) or \
                        (user_types is not None and user_type not in user_types):
                    return make_response(
                        errors=[
                            {
                                'code': 1,
                                'message': 'Access denied',
                                'source': 'authorization',
                                'path': '$.headers',
                                'additional': None
                            }
                        ],
                        status=403,
                        description='Ошибка доступа'
                    )

                g.token_pair = token_pair

            return f(*args, **kwargs)

        return decorated_function

    return decorator

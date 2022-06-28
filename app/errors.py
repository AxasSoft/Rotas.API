"""
Пользовательские обработчики ошибок
"""

from werkzeug.exceptions import HTTPException

from app import app, db
from utils.helpers import make_response
from utils.validation import InvalidRequestError, NotAllowedContentTypeError, NoBodyError


@app.errorhandler(InvalidRequestError)
def humanize(exc):
    human_errors = []

    errors_description = []

    for error in exc.errors:

        if isinstance(error, NotAllowedContentTypeError):
            human_errors.append(
                {
                    'code': 1,
                    'message': 'Incorrect content type header',
                    'source': 'headers',
                    'path': '$',
                    'additional': None,

                }
            )

            errors_description.append('Не поддерживаемы тип содержимого')

        elif isinstance(error, NoBodyError):
            human_errors.append(
                {
                    'code': 2,
                    'message': 'request body not provided or has incorrect syntax',
                    'source': 'body',
                    'path': '$',
                    'additional': None
                }
            )

            errors_description.append('Тело запроса не предоставлено или имеет некорректный синтаксис')

        else:
            schema_path = error.absolute_schema_path

            if schema_path[0] == 'additionalProperties':
                human_errors.append(
                    {
                        'code': 8,
                        'message': 'Additional fields are not allowed',
                        'source': error.custom_source,
                        'path': error.custom_path,
                        'additional': None
                    }
                )

                errors_description.append('Дополнительные поля запррещены')

            elif schema_path[-1] == 'required':
                human_errors.append(
                    {
                        'code': 3,
                        'message': 'Required field not provided',
                        'source': error.custom_source,
                        'path': error.custom_path,
                        'additional': None
                    }
                )

                errors_description.append('Не все обязательные поля  были переданны')

            elif schema_path[-1] == 'type':
                human_errors.append(
                    {
                        'code': 4,
                        'massage': 'Invalid field type',
                        'source': error.custom_source,
                        'path': error.custom_path,
                        'additional': {
                            'allowed types': error.validator_value
                        }
                    }
                )

                errors_description.append('Одно из полей имеет неправильный тип')

            else:
                human_errors.append(
                    {
                        'code': 5,
                        'message': 'Invalid field value',
                        'source': error.custom_source,
                        'path': error.custom_path,
                        'additional': {
                            'validator': {
                                'name': schema_path[-1],
                                'value': error.validator_value
                            }
                        }
                    }
                )

                errors_description.append('Одно из полей содержит некорректное значение.')

    description = ''+('\n'.join(set(errors_description)))

    return make_response(
        errors=human_errors,
        status=400,
        description=description
    )


@app.errorhandler(404)
def not_found_error(error):
    return make_response(
        errors=[
            {
                'code': 3,
                'message': 'Resource not found',
                'source': 'url',
                'path': '$',
                'additional': None
            }
        ],
        status=404,
        description='Страница не найдена'

    )


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return make_response(
        errors=[
            {
                'code': 1,
                'message': 'Internal server error',
                'source': None,
                'path': None,
                'additional': None
            }
        ],
        status=500,
        description='Внутреняя ошибка сервера'

    )


@app.errorhandler(HTTPException)
def handle_exception(e):
    """Return JSON instead of HTML for HTTP errors."""
    # start with the correct headers and status code from the error
    response = e.get_response()
    return make_response(
        errors=[
            {
                'code': 1,
                'message': response.status,
                'source': None,
                'path': None,
                'additional': {
                    "code": e.code,
                    "name": e.name,
                    "description": e.description
                }
            }
        ],
        status=e.code,
        description='Необработанная ошибка. '+e.description
    )

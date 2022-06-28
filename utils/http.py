from urllib.parse import urlparse

from colorama import Fore, Style


def get_raw_request(r):

    """
    :param r: пытается получить сырой текст запроса
    :return: сырой текст запроса
    """

    url = urlparse(r.url)
    text = r.method + ' ' + url.path
    if len(url.query) > 0:
        text += '?' + url.query
    text += ' ' + r.environ.get('SERVER_PROTOCOL') + '\r\n'

    for name, value in r.headers.items():
        text += f'{name}: {value}\r\n'

    length = r.content_length

    if length is not None:
        text += '\r\n' + r.get_data(as_text=True)

    return text


def get_raw_response(r, version, terminal_mode=True):
    text = version + ' ' + r.status + '\r\n'

    for name, value in r.headers.items():
        text += f'{name}: {value}\r\n'

    encoding = r.charset
    if encoding is None:
        encoding = 'utf-8'

    if (r.headers.get('Content-Type',) or '').startswith('text/html'):
        body = 'html body'
    else:

        body = None

        try:
            body = r.get_data(as_text=True)
        except Exception:
            if terminal_mode:
                print(Fore.YELLOW + 'Failed to read response body\r\n' + Style.RESET_ALL)

        if body is None:
            if terminal_mode:
                body = Fore.LIGHTBLACK_EX + "--- binary data ---" + Style.RESET_ALL
            else:
                body = "--- binary data ---"

    if body is not None and len(body) > 0:
        text += '\r\n' + body

    return text

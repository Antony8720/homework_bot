import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (EndpointUnavailable, EnvironmentVariableError,
                        JsonError, SendingMessageError, UnknownStatus)


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logger = logging.getLogger('__name__')


def send_message(bot, message):
    """Отправляет сообщения в телеграм чат."""
    try:
        logger.info('Начало отправки сообщения')
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        raise SendingMessageError(f'Ошибка отправки сообщения: {error}')
    else:
        logger.info('Сообщение успешно отправлено')


def get_api_answer(current_timestamp):
    """Делает запрос к эндпоинту."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    request_params = {
        'headers': HEADERS,
        'params': params
    }
    try:
        server_response = requests.get(ENDPOINT, **request_params)
    except Exception as error:
        raise EndpointUnavailable(f'Эндпоинт недоступен: {error}'
                                  f'Параметры запроса: {request_params}')
    if server_response.status_code != HTTPStatus.OK:
        status_code = server_response.status_code
        logger.error(f'Ошибка: {status_code}')
        raise Exception(f'Ошибка: {status_code}')
    try:
        return server_response.json()
    except Exception as error:
        raise JsonError(f'Ошибка парсинга json: {error}')


def check_response(response):
    """Проверяет ответ API на корректность."""
    if not isinstance(response, dict):
        raise TypeError('Ответ API не является словарем')
    try:
        homeworks = response['homeworks']
    except KeyError:
        raise KeyError('В словаре отсутсвует ключ homeworks')
    try:
        homework = homeworks[0]
    except IndexError:
        raise IndexError('Список домашних работ пуст')
    return homework


def parse_status(homework):
    """Извлекает из информации о домашней работе статус этой работы."""
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует ключ homework_name в ответе API')
    if 'status' not in homework:
        raise KeyError('Отсутствует ключ homework_status в ответе API')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in VERDICTS:
        logger.error(f'Неизвестный статус работы:{homework_status}')
        raise UnknownStatus(f'Неизвестный статус работы:{homework_status}')
    verdict = VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    if all([TELEGRAM_TOKEN,
           TELEGRAM_CHAT_ID,
           PRACTICUM_TOKEN]):
        return True
    else:
        logger.critical('Отсутствуют обязательные переменные окружения')
        return False


def main():
    """Основная логика работы бота."""
    logging.basicConfig(
        level=logging.INFO,
        filename='main.log',
        format='%(asctime)s, %(levelname)s, %(funcName)s, %(lineno)d, \
        %(name)s, %(message)s',
        filemode='w'
    )
    if not check_tokens():
        logging.critical('Отсутствует переменная окружения!')
        raise EnvironmentVariableError('Отсутствует переменная окружения')
    check_duplication = ''
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            try:
                response = get_api_answer(current_timestamp)
            except EndpointUnavailable as error:
                logger.error(f'Эндпоинт недоступен: {error}')
            except JsonError as error:
                logger.error(f'Ошибка парсинга json: {error}')
            try:
                homeworks = check_response(response)
            except KeyError as error:
                logger.error(f'В словаре отсутсвует ключ homeworks: {error}')
            except IndexError as error:
                logger.error(f'Список домашних работ пуст: {error}')
            if homeworks:
                message = parse_status(homeworks)
                try:
                    send_message(bot, message)
                except SendingMessageError as error:
                    logger.error(f'Ошибка отправки сообщения:{error}')
            current_timestamp = int(time.time())
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if message != check_duplication:
                send_message(bot, message)
                check_duplication = message
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()

import os
import sys
import time
import requests
import telegram
import telegram.ext
import logging

from dotenv import load_dotenv


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка доступности всех токенов"""

    if (PRACTICUM_TOKEN is None or TELEGRAM_TOKEN is None
       or TELEGRAM_CHAT_ID is None):
        logging.critical('Переменная окружения не обнаружена')
        sys.exit()


def send_message(bot, message):
    """Отправка сообщений"""

    try:
        logging.debug('Успешная отправка сообщения')
        return bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        logging.error(f'Ошибка при отправке сообщения: {error}')


def get_api_answer(timestamp):
    """Получение ответа API"""

    params = {'from_date': timestamp}

    try:
        response = requests.get(ENDPOINT, HEADERS, params)
        response.raise_for_status()
    except requests.HTTPError as http_error:
        print(f'HTTP error occurred: {http_error}')
        return None
    except requests.RequestException as error:
        print(f"An Error Occurred: {error}")
        return None
    assert response.status_code == 200, (f'API returned status code'
                                         f'{response.status_code}')
    return response.json()


def check_response(response):
    """Проверка ответа"""

    if not isinstance(response, dict):
        raise TypeError('Ожидался словарь в качестве ответа')

    if 'homeworks' not in response:
        raise KeyError('Ожидался ключ "homeworks" в ответе')

    homeworks = response.get('homeworks')

    if not isinstance(homeworks, list):
        raise TypeError("Ожидался список в качестве ответа")

    return True


def parse_status(homework):
    """Уведомление о статусе домашней работы"""

    if not isinstance(homework, dict):
        raise TypeError('Ожидался словарь в качестве ответа')

    if 'homework_name' not in homework:
        raise KeyError('Ожидался ключ "homework_name" в ответе')

    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')

    if homework_status not in HOMEWORK_VERDICTS:
        raise ValueError(f"Undocumented homework status: {homework_status}")

    return (f'Изменился статус проверки работы "{homework_name}".'
            f'{HOMEWORK_VERDICTS[homework_status]}')


def main():
    """Основная логика работы бота."""

    check_tokens()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            new_homework = get_api_answer(timestamp)
            if check_response(new_homework):
                try:
                    send_message(bot, parse_status
                                 (new_homework.get('homeworks')[0])
                                 )
                except Exception as error:
                    message = f'Ошибка при отправке сообщения: {error}'
                    logging.error(message)
            time.sleep(RETRY_PERIOD)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            logging.error(f'Сбой в работе программы: {error}')
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        filename='main.log',
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler]
    )
    main()

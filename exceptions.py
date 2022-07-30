class SendingMessageError(Exception):
    """Ошибка отправки сообщения."""

    pass


class EndpointUnavailable(Exception):
    """Ошибка недоступности эндпоинта."""

    pass


class JsonError(Exception):
    """Ошибка парсинга json."""

    pass


class EnvironmentVariableError(Exception):
    """Ошибка переменной окружения."""

    pass


class UnknownStatus(Exception):
    """Неизвестный статус работы."""

    pass

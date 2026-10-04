"""Ошибки, текст которых показывается пользователю."""


class ValidationError(Exception):
    """Ошибка ввода или нарушение правила из п. 4.1.4 ТЗ.

    Attributes:
        field: Название поля, в котором ошибка.
        message: Причина ошибки (п. 4.1.6 ТЗ).
    """

    def __init__(self, field: str, message: str):
        """Сохраняет поле и причину ошибки.

        Args:
            field: Название поля, например «Логин».
            message: Текст для пользователя.
        """
        super().__init__(message)
        self.field = field
        self.message = message


class AccessError(Exception):
    """Действие запрещено для роли пользователя (п. 4.1.9 ТЗ)."""


def require(value, field: str) -> str:
    """Проверяет, что обязательное поле заполнено.

    Args:
        value: Значение поля.
        field: Название поля для сообщения об ошибке.

    Returns:
        Значение без пробелов по краям.

    Raises:
        ValidationError: Если поле пустое.
    """
    text = str(value or "").strip()
    if not text:
        raise ValidationError(field, f"Поле «{field}» не заполнено.")
    return text

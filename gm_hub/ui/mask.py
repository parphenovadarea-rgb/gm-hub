"""Поле ввода по маске: пользователь вводит только цифры, а точки и
двоеточие программа ставит сама (дата «ДД.ММ.ГГГГ», время «ЧЧ:ММ»).
"""

from PySide6.QtWidgets import QLineEdit

DATE_MASK = "ДД.ММ.ГГГГ"
TIME_MASK = "ЧЧ:ММ"


def apply_mask(text: str, mask: str) -> str:
    """Расставляет разделители маски между цифрами.

    Разделитель добавляется только перед следующей цифрой, поэтому
    Backspace удаляет его обычным образом.

    Args:
        text: Введённый текст, в нём берутся только цифры.
        mask: Маска, например «ДД.ММ.ГГГГ»; буквы — места для цифр.

    Returns:
        Текст с разделителями, например «27092026» -> «27.09.2026».
    """
    digits = [ch for ch in text if ch.isdigit()]
    result = ""
    for ch in mask:
        if not digits:
            break
        result += digits.pop(0) if ch.isalpha() else ch
    return result


class MaskedEntry(QLineEdit):
    """Поле ввода, которое само ставит разделители по маске."""

    def __init__(self, mask: str):
        """Создаёт поле.

        Args:
            mask: Маска, например DATE_MASK или TIME_MASK.
        """
        super().__init__()
        self.mask = mask
        self.setPlaceholderText(mask)
        self.textEdited.connect(self.on_edit)

    def on_edit(self, text: str) -> None:
        """После ввода переписывает текст по маске."""
        new_text = apply_mask(text, self.mask)
        if new_text == text:
            return
        # курсор ставим после того же числа цифр, что было до него
        before = sum(ch.isdigit() for ch in text[: self.cursorPosition()])
        position = 0
        while position < len(new_text) and before > 0:
            if new_text[position].isdigit():
                before -= 1
            position += 1
        self.setText(new_text)
        self.setCursorPosition(position)

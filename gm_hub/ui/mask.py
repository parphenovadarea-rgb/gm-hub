"""Поле ввода по маске: пользователь вводит только цифры, а точки и
двоеточие программа ставит сама (дата «ДД.ММ.ГГГГ», время «ЧЧ:ММ»).
"""

from tkinter import ttk

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


class MaskedEntry(ttk.Entry):
    """Поле ввода, которое само ставит разделители по маске."""

    def __init__(self, parent, mask: str, **kwargs):
        """Создаёт поле.

        Args:
            parent: Родительский виджет.
            mask: Маска, например DATE_MASK или TIME_MASK.
            **kwargs: Остальные параметры ttk.Entry.
        """
        super().__init__(parent, **kwargs)
        self.mask = mask
        self.bind("<KeyRelease>", self.on_key)

    def on_key(self, _event=None):
        """После нажатия клавиши переписывает текст по маске."""
        text = self.get()
        new_text = apply_mask(text, self.mask)
        if new_text == text:
            return
        # курсор ставим после того же числа цифр, что было до него
        before = sum(ch.isdigit() for ch in text[: self.index("insert")])
        position = 0
        while position < len(new_text) and before > 0:
            if new_text[position].isdigit():
                before -= 1
            position += 1
        self.delete(0, "end")
        self.insert(0, new_text)
        self.icursor(position)

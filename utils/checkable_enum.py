from enum import Enum
from typing import List


class CheckableEnum(Enum):
    """
    Перечисление с возможностью проверки на наличие значения
    """

    @classmethod
    def has_value(cls, value: int) -> bool:
        """
        :param value: проверяемое значение
        :return: присутствует ли значение в перечислении

        Проверяет наличие значения в перечислении
        """
        return value in cls._value2member_map_

    @classmethod
    def get_values(cls) -> List[str]:
        """
        :return: Список числовых значений перечисления

        Получает список числовых значений перечисления
        """
        return list(cls._value2member_map_.keys())

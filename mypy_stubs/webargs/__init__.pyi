from typing import Any


class fields:
    @staticmethod
    def Int() -> Any: ...

    @staticmethod
    def Str() -> Any: ...

    @staticmethod
    def List(t: Any) -> Any: ...

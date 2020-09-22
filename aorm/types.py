from typing import Protocol, Dict

from sqlalchemy.util import classproperty


class RecordMappingField(str):
    def __init__(self, _):
        self.table = None
        super().__init__()


class RecordMapping(Protocol):
    __dataclass_fields__: Dict

    @classproperty
    def table_name(cls):
        return cls.__name__.lower()

    def __init_subclass__(cls, **kwargs):
        for i in cls.__annotations__:
            f = RecordMappingField(i)
            f.table = cls
            setattr(cls, i, f)

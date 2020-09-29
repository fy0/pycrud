from typing import Protocol, Dict, Optional, Any

from sqlalchemy.util import classproperty


class RecordMappingField(str):
    def __init__(self, _):
        self.table: Optional['RecordMapping'] = None
        super().__init__()


class RecordMapping(Protocol):
    id: Any
    __dataclass_fields__: Dict

    @classproperty
    def name(cls):
        return cls.__name__.lower()

    def __init_subclass__(cls, **kwargs):
        for i in cls.__annotations__:
            f = RecordMappingField(i)
            f.table = cls
            setattr(cls, i, f)

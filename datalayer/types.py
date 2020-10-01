from typing import Protocol, Dict, Optional, Any

from datalayer.cls_property import classproperty
from datalayer.utils import camel_case_to_underscore_case


class RecordMappingField(str):
    def __init__(self, _):
        self.table: Optional['RecordMapping'] = None
        super().__init__()


class RecordMapping(Protocol):
    id: Any
    __dataclass_fields__: Dict

    all_mappings = {}

    @classproperty
    def name(cls):
        return cls.__name__.lower()

    def __init_subclass__(cls, **kwargs):
        cls.all_mappings[camel_case_to_underscore_case(cls.__name__)] = cls
        for i in cls.__annotations__:
            f = RecordMappingField(i)
            f.table = cls
            setattr(cls, i, f)

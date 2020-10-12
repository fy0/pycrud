from typing import Dict, Optional, Any, Protocol, TypeVar, Set, Union, Literal

from pydantic import BaseModel, create_model

from querylayer.utils.cls_property import classproperty
from querylayer.utils.name_helper import camel_case_to_underscore_case


class RecordMappingField(str):
    def __init__(self, _):
        self.table: Optional['RecordMapping'] = None
        super().__init__()


class RecordMappingBase:
    id: Any

    all_mappings = {}

    partial_model: 'BaseModel' = None
    __dataclass_fields__: Dict

    @classproperty
    def name(cls):
        return camel_case_to_underscore_case(cls.__name__)

    def __init_subclass__(cls, **kwargs):
        cls.all_mappings[camel_case_to_underscore_case(cls.__name__)] = cls
        for i in cls.__annotations__:
            f = RecordMappingField(i)
            f.table = cls
            setattr(cls, i, f)

    @classmethod
    def from_data(cls, data):
        pass

    @property
    def fk_extra(self):
        return getattr(self, '$extra', None)


class RecordMapping(BaseModel, RecordMappingBase):
    @classmethod
    def to_partial(cls):
        return cls.clone(to_optional='__all__')

    @classmethod
    def clone(
        cls,
        *,
        fields: Set[str] = None,
        exclude: Set[str] = None,
        to_optional: Union[Literal['__all__'], Set[str], Dict[str, Any]] = None
    ) -> 'RecordMapping':
        if fields is None:
            fields = set(cls.__fields__.keys())

        if exclude is None:
            exclude = set()

        if to_optional == '__all__':
            opt = {f: None for f in fields}
            opt.update(cls.__field_defaults__)
        elif isinstance(to_optional, set):
            opt = {f: None for f in to_optional}
            opt.update(cls.__field_defaults__)
        else:
            opt = cls.__field_defaults__.copy()
            opt.update(to_optional or {})

        model = create_model(
            '*partial_' + cls.__name__,
            __base__=RecordMapping,
            **{
                field: (cls.__annotations__[field], opt.get(field, ...))
                for field in fields - exclude
            }
        )
        return model

    def __init_subclass__(cls, **kwargs):
        super(RecordMapping, cls).__init_subclass__()

        if cls.__name__.startswith('*partial_'):
            return

        cls.partial_model = cls.to_partial()

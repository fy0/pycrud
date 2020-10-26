import inspect
from typing import Dict, Optional, Any, Set, Union, List, TYPE_CHECKING, Callable, Awaitable

from pydantic import BaseModel, create_model
from typing_extensions import Literal

from pycurd.crud.query_result_row import QueryResultRow
from pycurd.utils.cls_property import classproperty
from pycurd.utils.name_helper import camel_case_to_underscore_case

if TYPE_CHECKING:
    from pycurd.query import QueryInfo
    from pycurd.values import ValuesToWrite
    from pycurd.crud.base_crud import PermInfo

IDList = List[Any]


class RecordMappingField(str):
    def __init__(self, _):
        self.table: Optional['RecordMapping'] = None
        super().__init__()

    def __repr__(self):
        return '%s.%s' % (self.table.table_name, str(self))


class RecordMappingBase:
    """
    before 和 after 的参数的大方向设计原则是，如果在这一callback中对参数进行修改，可以影响后续行为，则保留
    """
    id: Any

    all_mappings = {}

    record_fields: Dict[str, RecordMappingField]
    partial_model: 'BaseModel' = None

    @classproperty
    def table_name(cls):
        return camel_case_to_underscore_case(cls.__name__)

    @property
    def fk_extra(self):
        return getattr(self, '$extra', None)

    @classmethod
    async def on_query(cls, info: 'QueryInfo', perm: 'PermInfo' = None):
        """
        在发生查询时触发。
        触发接口：get list set delete
        :param info:
        :param perm:
        :return:
        """
        pass

    @classmethod
    async def on_read(cls,
                      info: 'QueryInfo',
                      when_complete: List[Callable[[List[QueryResultRow]], Awaitable]],
                      perm: 'PermInfo' = None):
        """
        触发接口：list insert(with returning) update(with returning)
        :param info:
        :param when_complete:
        :param perm:
        :return:
        """
        pass

    @classmethod
    async def on_insert(cls,
                        values_lst: List['ValuesToWrite'],
                        when_complete: List[Callable[[IDList], Awaitable]],
                        perm: 'PermInfo' = None):
        pass

    @classmethod
    async def on_update(cls,
                        info: 'QueryInfo',
                        values: 'ValuesToWrite',
                        when_before_update: List[Callable[[IDList], Awaitable]],
                        when_complete: List[Callable[[], Awaitable]],
                        perm: 'PermInfo' = None):
        """
        触发接口：update
        :param info:
        :param values:
        :param perm:
        :param when_before_update:
        :param when_complete:
        :return:
        """
        pass

    @classmethod
    async def on_delete(cls,
                        info: 'QueryInfo',
                        when_before_delete: List[Callable[[IDList], Awaitable]],
                        when_complete: List[Callable[[], Awaitable]],
                        perm: 'PermInfo' = None):
        pass


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

        def get_all_annotations():
            all_an = {}
            for i in inspect.getmro(cls)[::-1]:
                an = getattr(i, '__annotations__', None)
                if an:
                    all_an.update(an)
            return all_an

        all_an = get_all_annotations()
        model = create_model(
            '*partial_' + cls.__name__,
            __base__=RecordMapping,
            **{
                field: (all_an[field], opt.get(field, ...))
                for field in fields - exclude
            }
        )
        return model

    def __init_subclass__(cls, **kwargs):
        super(RecordMapping, cls).__init_subclass__()

        if cls.__name__.startswith('*partial_'):
            return

        cls.all_mappings[cls.table_name] = cls
        cls.record_fields = {}

        for i in cls.__fields__:
            f = RecordMappingField(i)
            f.table = cls
            setattr(cls, i, f)
            cls.record_fields[i] = f

        assert cls.record_fields.get('id'), 'id must be defined for %s' % cls
        cls.partial_model = cls.to_partial()

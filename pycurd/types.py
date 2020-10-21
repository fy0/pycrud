from typing import Dict, Optional, Any, Set, Union, List, TYPE_CHECKING

from pydantic import BaseModel, create_model
from typing_extensions import Literal

from pycurd.utils.cls_property import classproperty
from pycurd.utils.name_helper import camel_case_to_underscore_case

if TYPE_CHECKING:
    from pycurd.query import QueryInfo
    from pycurd.values import ValuesToWrite

IDList = List[Any]


class RecordMappingField(str):
    def __init__(self, _):
        self.table: Optional['RecordMapping'] = None
        super().__init__()

    def __repr__(self):
        return '%s.%s' % (self.table.table_name, str(self))


class RecordMappingBase:
    id: Any

    all_mappings = {}

    record_fields: Dict[str, RecordMappingField]
    partial_model: 'BaseModel' = None

    @classproperty
    def table_name(cls):
        return camel_case_to_underscore_case(cls.__name__)

    def __init_subclass__(cls, **kwargs):
        # 这块逻辑其实挺奇怪的 后面再说
        if cls.__name__ == 'RecordMapping':
            return

        cls.all_mappings[camel_case_to_underscore_case(cls.__name__)] = cls
        cls.record_fields = {}

        for i in cls.__annotations__:
            if i not in {'__annotations__', 'record_fields'}:
                f = RecordMappingField(i)
                f.table = cls
                setattr(cls, i, f)
                cls.record_fields[i] = f

    @property
    def fk_extra(self):
        return getattr(self, '$extra', None)

    @classmethod
    async def before_query(cls, info: 'QueryInfo'):
        """
        在发生查询时触发。
        触发接口：get list set delete
        :param info:
        :return:
        """
        pass

    async def after_read(self, records: List['RecordMappingBase']):
        """
        触发接口：get list new set
        :param records:
        :return:
        """
        pass

    async def before_insert(self, values_lst: List['ValuesToWrite']):
        """
        插入操作之前
        触发接口：new
        :param values_lst:
        :return:
        """
        pass

    async def after_insert(self, values_lst: List['ValuesToWrite'], records: List['RecordMappingBase']):
        """
        插入操作之后
        触发接口：new
        :param values_lst:
        :param records:
        :return:
        """
        pass

    async def before_update(self, values: 'ValuesToWrite', records: List['RecordMappingBase']):
        """
        触发接口：set
        :param values:
        :param records:
        :return:
        """
        pass

    async def after_update(self, values: 'ValuesToWrite', old_records: List['RecordMappingBase'],
                           new_records: List['RecordMappingBase']):
        """
        触发接口：set
        :param values:
        :param old_records:
        :param new_records:
        :return:
        """

    async def before_delete(self, records: List['RecordMappingBase']):
        """
        触发接口：delete
        :param records:
        :return:
        """
        pass

    async def after_delete(self, deleted_records: List['RecordMappingBase']):
        """
        触发接口：delete
        :param deleted_records:
        :return:
        """
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

        assert cls.record_fields.get('id'), 'id must be defined for %s' % cls
        cls.partial_model = cls.to_partial()

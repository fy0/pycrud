import asyncio
import inspect
from typing import Dict, Optional, Any, Set, Union, List, TYPE_CHECKING, Callable, Awaitable, Type

from pydantic import BaseModel, create_model
from typing_extensions import Literal

from pycrud.const import QUERY_OP_RELATION
from pycrud.crud.query_result_row import QueryResultRowList
from pycrud.dto_generator import DTOGenerator
from pycrud.utils import sentinel
from pycrud.utils.cls_property import classproperty
from pycrud.utils.name_helper import camel_case_to_underscore_case, get_class_full_name

if TYPE_CHECKING:
    from pycrud.query import QueryInfo
    from pycrud.values import ValuesToUpdate, ValuesToCreate
    from pycrud.crud.base_crud import PermInfo, BaseCrud

IDList = List[Any]


class EntityField:
    def __init__(self, s):
        self.name: str = s
        self.entity: Optional['Entity'] = None

    def __hash__(self):
        return hash(self.name)

    def __str__(self):
        return str(self.name)

    def __repr__(self):
        return '%s.%s' % (self.entity.table_name, str(self.name))

    def _condition_expr(self, op, other):
        from pycrud.query import ConditionExpr
        return ConditionExpr(self, op, other)

    def is_(self, other):
        from pycrud.query import ConditionExpr
        return ConditionExpr(self, QUERY_OP_RELATION.IS, other)

    def is_not(self, other):
        from pycrud.query import ConditionExpr
        return ConditionExpr(self, QUERY_OP_RELATION.IS_NOT, other)

    def __eq__(self, other):
        from pycrud.const import QUERY_OP_COMPARE
        return self._condition_expr(QUERY_OP_COMPARE.EQ, other)

    def __ne__(self, other):
        from pycrud.const import QUERY_OP_COMPARE
        return self._condition_expr(QUERY_OP_COMPARE.NE, other)

    def __le__(self, other):
        from pycrud.const import QUERY_OP_COMPARE
        return self._condition_expr(QUERY_OP_COMPARE.LE, other)

    def __lt__(self, other):
        from pycrud.const import QUERY_OP_COMPARE
        return self._condition_expr(QUERY_OP_COMPARE.LT, other)

    def __ge__(self, other):
        from pycrud.const import QUERY_OP_COMPARE
        return self._condition_expr(QUERY_OP_COMPARE.GE, other)

    def __gt__(self, other):
        from pycrud.const import QUERY_OP_COMPARE
        return self._condition_expr(QUERY_OP_COMPARE.GT, other)

    def contains(self, others: List[Any]):
        from pycrud.const import QUERY_OP_RELATION
        return self._condition_expr(QUERY_OP_RELATION.CONTAINS_ALL, others)

    def contains_any(self, other: Any):
        from pycrud.const import QUERY_OP_RELATION
        return self._condition_expr(QUERY_OP_RELATION.CONTAINS_ANY, other)

    def is_(self, other: Any):
        from pycrud.const import QUERY_OP_RELATION
        return self._condition_expr(QUERY_OP_RELATION.IS, other)

    def is_not(self, other: Any):
        from pycrud.const import QUERY_OP_RELATION
        return self._condition_expr(QUERY_OP_RELATION.IS_NOT, other)

    def in_(self, other: Any):
        from pycrud.const import QUERY_OP_RELATION
        return self._condition_expr(QUERY_OP_RELATION.IN, other)

    def not_in(self, other: Any):
        from pycrud.const import QUERY_OP_RELATION
        return self._condition_expr(QUERY_OP_RELATION.NOT_IN, other)

    def prefix_with(self, other: Any):
        from pycrud.const import QUERY_OP_RELATION
        return self._condition_expr(QUERY_OP_RELATION.PREFIX, other)


class EntityBase:
    """
    before 和 after 的参数的大方向设计原则是，如果在这一callback中对参数进行修改，可以影响后续行为，则保留
    """
    id: Any

    all_mappings: Dict[str, Type['EntityBase']] = {}

    record_fields: Dict[str, EntityField]
    partial_model: 'BaseModel' = None

    crud: 'BaseCrud'
    dto: DTOGenerator

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
    async def on_read(
            cls,
            info: 'QueryInfo',
            when_complete: List[Callable[[QueryResultRowList], Awaitable]],
            perm: 'PermInfo' = None
    ):
        """
        触发接口：list insert(with returning) update(with returning)
        :param info:
        :param when_complete:
        :param perm:
        :return:
        """
        pass

    @classmethod
    async def on_insert(
            cls,
            values_lst: List['ValuesToCreate'],
            when_complete: List[Callable[[IDList], Awaitable]],
            perm: 'PermInfo' = None
    ):
        pass

    @classmethod
    async def on_update(
            cls,
            info: 'QueryInfo',
            values: 'ValuesToUpdate',
            when_before_update: List[Callable[[IDList], Awaitable]],
            when_complete: List[Callable[[], Awaitable]],
            perm: 'PermInfo' = None
    ):
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
    async def on_delete(
            cls,
            info: 'QueryInfo',
            when_before_delete: List[Callable[[IDList], Awaitable]],
            when_complete: List[Callable[[], Awaitable]],
            perm: 'PermInfo' = None
    ):
        pass


class Entity(BaseModel, EntityBase):
    @classmethod
    def to_partial(cls):
        return cls.clone(to_optional='__all__', prefix='*partial_')

    @classmethod
    def clone(
        cls,
        *,
        fields: Set[str] = sentinel,
        exclude: Set[str] = sentinel,
        to_optional: Union[Literal['__all__'], Set[str], Dict[str, Any]] = None,
        prefix='*clone_',
        base_cls=sentinel
    ) -> 'Entity':
        if fields is sentinel:
            fields = set(cls.__fields__.keys())

        if exclude is sentinel:
            exclude = set()

        if base_cls is sentinel:
            base_cls = Entity

        fields_defaults = {}
        _missing = object()
        for k, v in cls.__fields__.items():
            val = getattr(v, 'default', _missing)
            if val != _missing:
                fields_defaults[k] = val

        if to_optional == '__all__':
            opt = {f: None for f in fields}
            opt.update(fields_defaults)
        elif isinstance(to_optional, set):
            opt = {f: None for f in to_optional}
            opt.update(fields_defaults)
        else:
            opt = fields_defaults.copy()
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
            prefix + cls.__name__,
            __base__=base_cls,
            **{
                # tip: {k: v for k,v in ...}
                field: (all_an[field], opt.get(field, ...))
                for field in fields - exclude
            }
        )
        return model

    def __init_subclass__(cls, **kwargs):
        super(Entity, cls).__init_subclass__()

        def check_hook(func):
            assert inspect.ismethod(func) and asyncio.iscoroutinefunction(func),\
                '%s must be async function with @classmethod' % get_class_full_name(func)

        check_hook(cls.on_query)
        check_hook(cls.on_insert)
        check_hook(cls.on_read)
        check_hook(cls.on_update)
        check_hook(cls.on_delete)

        if cls.__name__.startswith('*partial_'):
            return

        cls.all_mappings[cls.table_name] = cls
        cls.record_fields = {}

        for i in cls.__fields__:
            f = EntityField(i)
            f.entity = cls
            setattr(cls, i, f)
            cls.record_fields[i] = f

        assert cls.record_fields.get('id'), 'id must be defined for %s' % cls
        cls.partial_model = cls.to_partial()
        cls.dto = DTOGenerator(cls)

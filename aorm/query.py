from dataclasses import dataclass, field
from typing import List, Union, Set, Dict, Any, Type

from typing_extensions import Literal

from aorm.const import QUERY_OP_COMPARE, QUERY_OP_RELATION
from aorm.types import RecordMapping, RecordMappingField


class LogicRelation:
    def __init__(self, *args):
        pass

    def and_(self, *args):
        pass

    def or_(self, *args):
        pass


class QueryField:
    def __init__(self, field):
        self.field = field
        self._chains = []

    def binary(self, op: Union[QUERY_OP_COMPARE, QUERY_OP_RELATION], value):
        # check valid
        self._chains.append([self.field, op, value])
        return self


def f(field=None) -> Union[QueryField, LogicRelation]:
    if field is None:
        return LogicRelation()
    return QueryField(field)


@dataclass
class SelectExpr:
    """
    $ta.id
    """
    column: Union[RecordMappingField, Any]
    alias: str = None

    @property
    def table_name(self):
        return self.column.table.name


@dataclass
class SelectExprTree:
    """
    $ta: [
        SelectExpr(TableA, 'id')
    ]
    """
    items: List[Union[SelectExpr, 'SelectExprTree']]
    alias: str


class QueryField:
    def __init__(self, field):
        self.field = field
        self._chains = []

    def binary(self, op: Union[QUERY_OP_COMPARE, QUERY_OP_RELATION], value):
        # check valid
        self._chains.append([self.field, op, value])
        return self


@dataclass
class QueryOrder:
    column: RecordMappingField
    order: Union[Literal['asc', 'desc']]

    def __eq__(self, other):
        if isinstance(other, QueryOrder):
            return self.column == other.column and self.order == other.order
        return False

    def __repr__(self):
        return '<QueryOrder %r.%s>' % (self.column, self.order)


@dataclass
class ConditionExpr:
    """
    $ta:id.eq = 123
    $ta:id.eq = $tb:id
    """
    column: Union[RecordMappingField, Any]  # 实际类型是 RecordMappingField
    op: Union[QUERY_OP_COMPARE, QUERY_OP_RELATION]
    value: Union[SelectExpr, Any]

    @property
    def table_name(self):
        return self.column.table.name


@dataclass
class ConditionLogicExpr:
    type: Union[Literal['and'], Literal['or']]
    items: List[Union[ConditionExpr, 'ConditionLogicExpr']]


@dataclass
class QueryConditions:
    items: List[Union[ConditionExpr, 'ConditionLogicExpr']]

    @property
    def type(self):
        return 'and'


@dataclass
class QueryInfo:
    """
    {
        'username.eq': '111',
    }
    {
        '$or': {
            'username.eq': '111',
            'name.ne': '22'
        }
    }

    // 方案一
    // 方案问题：
    // 1. 如果只允许外部表join当前表，那么表达能力不如方案二；如果主表也能写涉及外部表的条件，自由度过大，容易写出奇怪的语句
    {
        '$select': 'aa, bb, cc', // 选中
        '$select-': 'dd, ee, ff', // 排除
        '$order-by': 'aa.desc, bb.asc',
        '$foreign-key': {
            'user_info': {  // 外联表名
                '$select': ...
                'id.eq': '$src.id'
            },
            'user_info[]': {  // 外联表名
                '$select': ...
                'id.eq': '$src.id'
            },
            'session': {
                'id.eq': '$user_info.id'  // 不能允许这个
            }
        },

        'time.gt': '$session.time', // 暂不允许inner join
    }
    // 关键字：$select、$select-，$order-by，$foreign-key

    // 方案二
    // 方案问题：
    // 1. value 有时是str 有时是表达式
    // 2. 如果不做限制，实际上任意一个接口都差不多具备全库查询能力
    // 3. join时候要区分inner outter还是有些复杂
    {
        '$from': 'ta', // 此为隐含条件，不需要直接写出
        '$from_others': ['tb'],  // join的表

        '$select': ['aa', 'bb', '$tb:cc', '$ta'], // $ta 代指ta表，返回json：{'aa': xx, 'bb': xx, '$tb:cc': xx, '$ta': xxx}
        '$select': {'aa': null, 'bb': null, '$tb:cc': 'cc', '$ta': 'a_info'],  // 返回结果同上 用value的名字覆盖上面的

        '$id.eq': '$tb:id', // select ... from ta, tb where ta.id = tb.id
        '$time.gt': 1,  // select ... from ta, tb where ta.time > 1
        '$tb:cc.eq': '$ta:id', // select ... from ta, tb where tb.cc = ta.id
        '$or': {
            '$user_id.eq': '11',
            '$user_id.eq': '22',
        }
    }
    // 关键字：$select、$select-，$order-by，$foreign-key，$or，$and
    """
    from_table: Type[RecordMapping]

    select: List[Union[RecordMappingField, Any]] = field(default_factory=lambda: [])
    select_exclude: Set[Union[RecordMappingField, Any]] = field(default_factory=lambda: set())

    # select: List[Union[SelectExpr, SelectExprTree]] = field(default_factory=lambda: [])
    # select_exclude: Dict[Type[RecordMapping], Set[str]] = None

    conditions: QueryConditions = None
    order_by: List = field(default_factory=lambda: [])

    foreign_keys: Dict[str, 'QueryInfo'] = None
    extra_variables: Dict[str, Any] = field(default_factory=lambda: {})

    offset: int = 0
    limit: int = 20

    @property
    def select_for_curd(self):
        return self.select
    #
    # def __post_init__(self):
    #     pass
    #     # self.from_all_tables = {self.from_default}

    def parse_query(self, data):
        pass

    def parse_json(self, data):
        for key, value in data.items():
            if key.startswith('$'):
                if key == '$select':
                    pass
                elif key == '$select-':
                    pass
                elif key == '$order-by':
                    pass
                if key == '$foreign-key':
                    pass
                elif key == '$or':
                    pass
                elif key == '$and':
                    pass

                continue

            if '.' in key:
                field_name, op = key.split('.', 1)
                self._parse_add_condition(field_name, op, value)

    def _parse_add_condition(self, field_name, op, value):
        if field_name in self.from_.__annotations__:
            self.conditions.append(f(field_name).binary(op, value))

    def to_json(self):
        return ''

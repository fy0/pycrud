import dataclasses
import json
from dataclasses import dataclass, field
from typing import List, Union, Set, Dict, Any, Type

from typing_extensions import Literal

from pycurd.const import QUERY_OP_COMPARE, QUERY_OP_RELATION, QUERY_OP_FROM_TXT
from pycurd.error import UnknownQueryOperator, InvalidQueryConditionValue
from pycurd.types import RecordMapping, RecordMappingField


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
        return self.column.table.table_name


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
    column: Union[RecordMappingField, Any]  # 实际类型是 RecordMappingField，且必须如此
    op: Union[QUERY_OP_COMPARE, QUERY_OP_RELATION]
    value: Union[RecordMappingField, Any]

    def __post_init__(self):
        assert isinstance(self.column, RecordMappingField), 'RecordMappingField excepted, got %s' % type(self.column)

    @property
    def table_name(self):
        return self.column.table.table_name


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
class QueryJoinInfo:
    table: Type[RecordMapping]
    conditions: QueryConditions
    type: Union[Literal['inner', 'left']] = 'left'
    limit: int = -1  # unlimited


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

    conditions: QueryConditions = None
    order_by: List = field(default_factory=lambda: [])

    foreign_keys: Dict[str, 'QueryInfo'] = None

    offset: int = 0
    limit: int = 20

    join: List[QueryJoinInfo] = None
    select_hidden: Set[Union[RecordMappingField, Any]] = field(default_factory=lambda: set())

    def clone(self):
        # TODO: it's shallow copy
        return dataclasses.replace(self)
        # d = dataclasses.asdict(self)
        # if 'conditions' in d:
        #     d['conditions'] = QueryConditions(**d['conditions'])
        # return QueryInfo(d)

    @property
    def select_for_curd(self):
        return self.select

    @classmethod
    def from_json(cls, table, data, from_http_query=False):
        assert table, 'table must be exists'
        get_items = lambda keys: [getattr(table, x) for x in keys]
        q = cls(table)

        def parse_select(select_text, unselect_text):
            if select_text is None:
                selected = get_items(table.record_fields.keys())
            else:
                selected_columns = list(filter(lambda x: x, map(str.strip, select_text.split(','))))
                selected = get_items(selected_columns)

            if unselect_text is not None:
                unselected_columns = list(filter(lambda x: x, map(str.strip, unselect_text.split(','))))
                unselected = get_items(unselected_columns)
            else:
                unselected = None

            return selected, unselected

        def parse_value(val):
            if isinstance(val, str) and val.startswith('$'):
                a, b = val.split(':', 1)
                t = RecordMapping.all_mappings.get(a[1:])
                return getattr(t, b)
            return val

        def parse_conditions(data):
            conditions = []

            def logic_op_check(key: str, op_prefix: str) -> bool:
                if key.startswith(op_prefix):
                    if len(key) == len(op_prefix):
                        return True
                    return key[len(op_prefix):].isdigit()
                return False

            for key, value in data.items():
                if key.startswith('$'):
                    if logic_op_check(key, '$or'):
                        conditions.append(ConditionLogicExpr('or', parse_conditions(value)))
                    elif logic_op_check(key, '$and'):
                        conditions.append(ConditionLogicExpr('and', parse_conditions(value)))

                elif '.' in key:
                    field_name, op_name = key.split('.', 1)
                    if from_http_query:
                        try:
                            value = json.loads(value)
                        except (TypeError, json.JSONDecodeError):
                            raise InvalidQueryConditionValue('right value must can be unserializable with json.loads')

                    op = QUERY_OP_FROM_TXT.get(op_name)
                    if op is None:
                        raise UnknownQueryOperator(op_name)

                    if op in (QUERY_OP_RELATION.IN, QUERY_OP_RELATION.NOT_IN, QUERY_OP_RELATION.CONTAINS, QUERY_OP_RELATION.CONTAINS_ANY):
                        assert isinstance(value, List), 'The right value of relation operator must be list'

                    conditions.append(ConditionExpr(getattr(table, field_name), op, value))

            return conditions

        q.select, q.select_exclude = parse_select(data.get('$select'), data.get('$select-'))
        q.conditions = QueryConditions(parse_conditions(data))

        for key, value in data.items():
            if key.startswith('$'):
                if key == '$order-by':
                    pass
                elif key == '$foreign-key':
                    pass

                continue

            if '.' in key:
                field_name, op = key.split('.', 1)
                # _parse__condition(field_name, op, value)

        return q

    def to_json(self):
        raise NotImplemented

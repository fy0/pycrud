import json
from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum
from functools import reduce
from typing import Dict, Type, Union, List, Iterable, Any, Tuple, Set

import pypika
from multidict import MultiDict
from pypika import Query, Order
from pypika.enums import Arithmetic, Comparator
from pypika.functions import Count, DistinctOptionFunction
from pypika.terms import ComplexCriterion, Parameter, Field as PypikaField, ArithmeticExpression, Criterion, \
    BasicCriterion

from pycrud.const import QUERY_OP_COMPARE, QUERY_OP_RELATION
from pycrud.crud.base_crud import BaseCrud
from pycrud.crud.query_result_row import QueryResultRow, QueryResultRowList
from pycrud.error import ValueTypeNotAllowed
from pycrud.permission import RoleDefine
from pycrud.query import QueryInfo, QueryConditions, ConditionLogicExpr, ConditionExpr, NegatedExpr
from pycrud.types import Entity, EntityField, IDList
from pycrud.utils.json_ex import json_dumps_ex
from pycrud.values import ValuesToUpdate, ValuesDataUpdateFlag, ValuesToCreate

_sql_method_map = {
    # '+': '__pos__',
    # '-': '__neg__',
    QUERY_OP_COMPARE.EQ: '__eq__',
    QUERY_OP_COMPARE.NE: '__ne__',
    QUERY_OP_COMPARE.LT: '__lt__',
    QUERY_OP_COMPARE.LE: '__le__',
    QUERY_OP_COMPARE.GE: '__ge__',
    QUERY_OP_COMPARE.GT: '__gt__',
    QUERY_OP_RELATION.IN: 'isin',
    QUERY_OP_RELATION.NOT_IN: 'notin',
    QUERY_OP_RELATION.IS: '__eq__',
    QUERY_OP_RELATION.IS_NOT: '__ne__',
    QUERY_OP_RELATION.CONTAINS_ALL: 'contains',
    QUERY_OP_RELATION.CONTAINS_ANY: '',
    QUERY_OP_RELATION.PREFIX: '',
}


class ArithmeticExt(Enum):
    concat = '||'


class ArrayMatchingExt(Comparator):
    contains = '@>'
    contains_any = '&&'


class PostgresArrayDistinct(Criterion):
    def __init__(self, expr, **kwargs):
        super().__init__(**kwargs)
        self._expr = expr

    def get_sql(self, **kwargs):
        return 'ARRAY(SELECT DISTINCT unnest(%s))' % self._expr.get_sql(**kwargs)


class PostgresArrayDifference(Criterion):
    def __init__(self, a, b, **kwargs):
        super().__init__(**kwargs)
        self._left = a
        self._right = b

    def get_sql(self, **kwargs):
        return 'array(SELECT unnest(%s) EXCEPT SELECT unnest(%s))' % (
            self._left.get_sql(**kwargs),
            self._right.get_sql(**kwargs)
        )


@dataclass
class PlaceHolderGenerator:
    template: str = '?'  # sqlite
    # template: str = '${count}'  # PostgreSQL
    # template: str = '%s'  # mysql
    json_dumps_func: Any = json_dumps_ex

    def __post_init__(self):
        self.count = 1
        self.keys = []
        self.values = []

    def next(self, value, *, left_is_array=False, left_is_json=False, contains_relation=False) -> Parameter:
        if left_is_array or contains_relation:
            key = self.template.format(count=self.count)
            p = Parameter(key)
            self.count += 1
            self.keys.append(key)
            self.values.append(value)

        elif left_is_json:
            key = self.template.format(count=self.count)
            p = Parameter(key)
            self.count += 1
            self.keys.append(key)
            self.values.append(self.json_dumps_func(value))

        elif isinstance(value, (List, Set, Tuple)):
            tmpls = []

            for i in value:
                key = self.template.format(count=self.count)
                self.keys.append(key)
                tmpls.append(key)
                self.count += 1

            self.values.extend(value)
            # if len(value) == 1:
            #     p = Parameter(f'({tmpls[0]},)')
            # else:
            tmpl1 = ', '.join(tmpls)
            p = Parameter(f'({tmpl1})')

        else:
            key = self.template.format(count=self.count)
            p = Parameter(key)
            self.count += 1
            self.keys.append(key)
            self.values.append(value)

        return p


@dataclass
class SQLExecuteResult:
    lastrowid: Any
    values: Iterable = None

    def __iter__(self):
        return iter(self.values)


InsertValueTypes = Union[ValuesToCreate, Entity, Dict, MultiDict]


class SQLCrud(BaseCrud):
    _permission: List[RoleDefine]
    entity2model: Dict[Type[Entity], Union[str, pypika.Table]]

    def __init__(self, permission: List[RoleDefine], entity2model: Dict[Type[Entity], Union[str, pypika.Table]]):
        super(SQLCrud, self).__init__(permission)
        self.entity2model = entity2model

    def __post_init__(self):
        super(SQLCrud, self).__post_init__()

        self.json_dumps_func = json_dumps_ex
        self._table_cache = {
            # 'mapping': {
            #     'array_fields': [],
            #     'json_fields': [],
            # }
        }

        for k, v in self.entity2model.items():
            k.crud = self

            if isinstance(v, str):
                self.entity2model[k] = pypika.Table(v)

            self._table_cache[k] = {
                'array_fields': set(),
                'json_fields': set(),
            }

    async def insert_many(self, entity: Type[Entity], values_list: Iterable[InsertValueTypes], *, _perm=None) -> IDList:
        """
        Insert multiple entries.
        return id list if succeed.
        `entity.on_insert` will be called before insert operation.

        :param entity:
        :param values_list:
        :param _perm:
        :return:
        """
        when_complete = []

        values_list_new = []
        for i in values_list:
            if isinstance(i, ValuesToCreate):
                values_list_new.append(i)
            elif isinstance(i, (Entity, Dict, MultiDict)):
                values_list_new.append(ValuesToCreate(i, entity))
            else:
                raise ValueTypeNotAllowed('value type not allowed: ', type(i))

        values_list = values_list_new

        for i in values_list:
            i.bind(entity)

        await entity.on_insert(values_list, when_complete, _perm)

        model = self.entity2model[entity]
        tc = self._table_cache[entity]
        sql_lst = []

        for i in values_list:
            phg = self.get_placeholder_generator()
            sql = Query().into(model).columns(*i.keys()).insert(
                *[phg.next(_b, left_is_array=_a in tc['array_fields'], left_is_json=_a in tc['json_fields']) for _a, _b in i.items()]
            )
            sql_lst.append([sql, phg])

        ret = []
        for i in sql_lst:
            ret.append(await self.execute_sql(i[0].get_sql(), i[1]))

        id_lst = [x.lastrowid for x in ret]
        for i in when_complete:
            await i(id_lst)

        return id_lst

    async def update(self, info: QueryInfo, values: ValuesToUpdate, *, _perm=None) -> IDList:
        """
        Update multiple data.
        Select data with `info`, update with `values`.
        return id list if succeed.

        `entity.on_query` will be called before select operation.
        `entity.on_update` will be called before update operation.

        :param info:
        :param values:
        :param _perm:
        :return:
        """
        # hook
        await info.entity.on_query(info, _perm)
        when_before_update, when_complete = [], []
        values.bind(info.entity)
        await info.entity.on_update(info, values, when_before_update, when_complete, _perm)

        model = self.entity2model[info.entity]
        tc = self._table_cache[info.entity]
        qi = info.clone()
        qi.select = []
        lst = await self.get_list(qi, _perm=_perm)
        id_lst = [x.id for x in lst]

        for i in when_before_update:
            await i(id_lst)

        if id_lst:
            # 选择项
            phg = self.get_placeholder_generator()
            sql = Query().update(model)
            for k, v in values.items():
                vflag = values.data_flag.get(k)

                val = phg.next(v, left_is_array=k in tc['array_fields'], left_is_json=k in tc['json_fields'])

                if vflag:
                    if vflag == ValuesDataUpdateFlag.INCR:
                        # f'{k} + {val}'
                        sql = sql.set(k, ArithmeticExpression(Arithmetic.add, PypikaField(k), val))

                    elif vflag == ValuesDataUpdateFlag.DECR:
                        # f'{k} - {val}'
                        sql = sql.set(k, ArithmeticExpression(Arithmetic.sub, PypikaField(k), val))

                    elif vflag == ValuesDataUpdateFlag.ARRAY_EXTEND:
                        # f'{k} || {val}'
                        vexpr = ArithmeticExpression(ArithmeticExt.concat, PypikaField(k), val)
                        sql = sql.set(k, vexpr)

                    elif vflag == ValuesDataUpdateFlag.ARRAY_PRUNE:
                        # TODO: 现在prune也会去重，这是不对的
                        # f'array(SELECT unnest({k}) EXCEPT SELECT unnest({val}))'
                        vexpr = PostgresArrayDifference(PypikaField(k), val)
                        sql = sql.set(k, vexpr)

                    elif vflag == ValuesDataUpdateFlag.ARRAY_EXTEND_DISTINCT:
                        # f'ARRAY(SELECT DISTINCT unnest({k} || {val}))'
                        vexpr = PostgresArrayDistinct(ArithmeticExpression(ArithmeticExt.concat, PypikaField(k), val))
                        sql = sql.set(k, vexpr)

                    elif vflag == ValuesDataUpdateFlag.ARRAY_PRUNE_DISTINCT:
                        vexpr = PostgresArrayDifference(PypikaField(k), val)
                        sql = sql.set(k, vexpr)

                else:
                    sql = sql.set(k, val)

            # 注意：生成的SQL顺序和values顺序的对应关系
            sql = sql.where(model.id.isin(phg.next(id_lst)))
            await self.execute_sql(sql.get_sql(), phg)

        for i in when_complete:
            await i()

        return id_lst

    async def delete(self, info: QueryInfo, *, _perm=None) -> IDList:
        """
        Delete multiple data.
        Select data with `info`.
        return id list if succeed.

        `entity.on_query` will be called before select operation.
        `entity.on_delete` will be called before update operation.

        :param info:
        :param _perm:
        :return:
        """
        model = self.entity2model[info.entity]
        when_before_delete, when_complete = [], []
        await info.entity.on_delete(info, when_before_delete, when_complete, _perm)

        qi = info.clone()
        qi.select = []
        lst = await self.get_list(qi, _perm=_perm)

        # 选择项
        id_lst = [x.id for x in lst]

        for i in when_before_delete:
            await i(id_lst)

        if id_lst:
            phg = self.get_placeholder_generator()
            sql = Query().from_(model).delete().where(model.id.isin(phg.next(id_lst)))
            await self.execute_sql(sql.get_sql(), phg)

        for i in when_complete:
            await i()

        return id_lst

    async def get_list(self, info: QueryInfo, return_with_rows_count=False, *, _perm=None) -> QueryResultRowList:
        """
        Select multiple data.
        Select data with `info`.

        `entity.on_query` will be called before select operation.
        `entity.on_read` will be called before select operation.

        :param info:
        :param return_with_rows_count:
        :param _perm:
        :return:
        """
        # hook
        await info.entity.on_query(info, _perm)
        when_complete = []
        await info.entity.on_read(info, when_complete, _perm)

        model = self.entity2model[info.entity]

        # 选择项
        q = Query()
        q = q.from_(model)

        select_fields = [model.id]
        for i in info.select_for_crud:
            select_fields.append(getattr(self.entity2model[i.entity], i.name))

        q = q.select(*select_fields)
        phg = self.get_placeholder_generator()

        # 构造条件
        if info.conditions:
            def solve_condition(c):
                if isinstance(c, QueryConditions):
                    items = list([solve_condition(x) for x in c.items])
                    if items:
                        return reduce(ComplexCriterion.__and__, items)  # 部分orm在实现join条件的时候拼接的语句不正确

                elif isinstance(c, (QueryConditions, ConditionLogicExpr)):
                    items = [solve_condition(x) for x in c.items]
                    if items:
                        if c.type == 'and':
                            return reduce(ComplexCriterion.__and__, items)
                        else:
                            return reduce(ComplexCriterion.__or__, items)

                elif isinstance(c, ConditionExpr):
                    field = getattr(self.entity2model[c.column.entity], c.column.name)

                    if isinstance(c.value, EntityField):
                        real_value = getattr(self.entity2model[c.value.entity], c.value.name)
                    else:
                        contains_relation = c.op in (QUERY_OP_RELATION.CONTAINS_ALL,
                                                     QUERY_OP_RELATION.CONTAINS_ANY)

                        # value = [c.value] if c.op == QUERY_OP_RELATION.CONTAINS_ANY else c.value
                        if c.op in (QUERY_OP_RELATION.PREFIX, QUERY_OP_RELATION.IPREFIX):
                            # TODO: 更好的安全机制，防止利用like语句
                            c.value = c.value.replace('%', '')
                            c.value = c.value + '%'
                        real_value = phg.next(c.value, contains_relation=contains_relation)

                    if c.op == QUERY_OP_RELATION.PREFIX:
                        cond = field.like(real_value)
                    elif c.op == QUERY_OP_RELATION.IPREFIX:
                        cond = field.ilike(real_value)
                    elif c.op == QUERY_OP_RELATION.CONTAINS_ANY:
                        # &&
                        cond = BasicCriterion(ArrayMatchingExt.contains_any, field, field.wrap_constant(real_value))
                    else:
                        cond = getattr(field, _sql_method_map[c.op])(real_value)
                    return cond

                elif isinstance(c, NegatedExpr):
                    return ~solve_condition(c.expr)

            if info.join:
                for ji in info.join:
                    jtable = self.entity2model[ji.table]
                    where = solve_condition(ji.conditions)

                    if ji.limit == -1:
                        q = q.inner_join(jtable).on(where)
                    else:
                        q = q.inner_join(jtable).on(
                            jtable.id == Query.from_(jtable).select(jtable.id).where(where).limit(ji.limit)
                        )

            ret = solve_condition(info.conditions)
            if ret:
                q = q.where(ret)

        ret = QueryResultRowList()

        # rows count
        if return_with_rows_count:
            bak = q._selects
            q._selects = [Count('1')]
            cursor = await self.execute_sql(q.get_sql(), phg)
            ret.rows_count = next(iter(cursor))[0]
            q._selects = bak

        # 一些限制
        if info.order_by:
            order_dict = {
                'default': None,
                'desc': Order.desc,
                'asc': Order.asc
            }
            for i in info.order_by:
                q = q.orderby(i.column.name, order=order_dict[i.order])
        if info.limit != -1:
            q = q.limit(info.limit)
        q = q.offset(info.offset)

        # 查询结果
        cursor = await self.execute_sql(q.get_sql(), phg)

        for i in cursor:
            it = iter(i)
            ret.append(QueryResultRow(next(it), list(it), info, info.table))

        for i in when_complete:
            await i(ret)

        return ret

    @abstractmethod
    def get_placeholder_generator(self) -> PlaceHolderGenerator:
        pass

    @abstractmethod
    async def execute_sql(self, sql, phg: PlaceHolderGenerator):
        pass

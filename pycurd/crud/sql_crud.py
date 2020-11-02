import json
from abc import abstractmethod
from dataclasses import dataclass
from functools import reduce
from typing import Dict, Type, Union, List, Iterable, Any, Tuple, Set

import pypika
from pypika import Query
from pypika.terms import ComplexCriterion, Parameter

from pycurd.const import QUERY_OP_COMPARE, QUERY_OP_RELATION
from pycurd.crud.base_crud import BaseCrud
from pycurd.crud.query_result_row import QueryResultRow
from pycurd.query import QueryInfo, QueryConditions, ConditionLogicExpr, ConditionExpr
from pycurd.types import RecordMapping, RecordMappingField, IDList
from pycurd.values import ValuesToWrite

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
    QUERY_OP_RELATION.CONTAINS: 'contains',
    QUERY_OP_RELATION.CONTAINS_ANY: 'has_any_keys',
    QUERY_OP_RELATION.PREFIX: 'startswith',
}


@dataclass
class PlaceHolderGenerator:
    template: str = '?'  # sqlite
    # template: str = '${count}'  # PostgreSQL
    # template: str = '%s'  # mysql

    def __post_init__(self):
        self.count = 1
        self.values = []

    def next(self, value, *, is_array=False, is_json=False) -> Parameter:
        if is_array:
            p = Parameter(self.template.format(count=self.count))
            self.count += 1
            self.values.append(value)

        elif is_json:
            p = Parameter(self.template.format(count=self.count))
            self.count += 1
            self.values.append(json.dumps(value))

        elif isinstance(value, (List, Set, Tuple)):
            tmpls = []

            for i in value:
                tmpls.append(self.template.format(count=self.count))
                self.count += 1

            self.values.extend(value)
            # if len(value) == 1:
            #     p = Parameter(f'({tmpls[0]},)')
            # else:
            tmpl1 = ', '.join(tmpls)
            p = Parameter(f'({tmpl1})')

        else:
            p = Parameter(self.template.format(count=self.count))
            self.count += 1
            self.values.append(value)

        return p


@dataclass
class SQLExecuteResult:
    lastrowid: Any
    values: Iterable = None

    def __iter__(self):
        return iter(self.values)


@dataclass
class SQLCrud(BaseCrud):
    mapping2model: Dict[Type[RecordMapping], Union[str, pypika.Table]]

    def __post_init__(self):
        self._table_cache = {
            # 'mapping': {
            #     'array_fields': [],
            #     'json_fields': [],
            # }
        }

        for k, v in self.mapping2model.items():
            if isinstance(v, str):
                self.mapping2model[k] = pypika.Table(v)

            self._table_cache[k] = {
                'array_fields': set(),
                'json_fields': set(),
            }

    async def insert_many(self, table: Type[RecordMapping], values_list: Iterable[ValuesToWrite], *, _perm=None) -> IDList:
        when_complete = []
        await table.on_insert(values_list, when_complete, _perm)

        model = self.mapping2model[table]
        tc = self._table_cache[table]
        sql_lst = []

        for i in values_list:
            phg = self.get_placeholder_generator()
            sql = Query().into(model).columns(*i.keys()).insert(
                *[phg.next(_b, is_array=_a in tc['array_fields'], is_json=_a in tc['json_fields']) for _a, _b in i.items()]
            )
            sql_lst.append([sql, phg])

        ret = []
        for i in sql_lst:
            ret.append(await self.execute_sql(i[0].get_sql(), i[1]))

        id_lst = [x.lastrowid for x in ret]
        for i in when_complete:
            await i(id_lst)

        return id_lst

    async def update(self, info: QueryInfo, values: ValuesToWrite, *, _perm=None) -> IDList:
        # hook
        await info.from_table.on_query(info)
        when_before_update, when_complete = [], []
        await info.from_table.on_update(info, values, when_before_update, when_complete, _perm)

        model = self.mapping2model[info.from_table]
        qi = info.clone()
        qi.select = []
        lst = await self.get_list(qi)
        id_lst = [x.id for x in lst]

        for i in when_before_update:
            await i(id_lst)

        # 选择项
        phg = self.get_placeholder_generator()
        sql = Query().update(model)
        for k, v in values.items():
            sql = sql.set(k, phg.next(v))

        # 注意：生成的SQL顺序和values顺序的对应关系
        sql = sql.where(model.id.isin(phg.next(id_lst)))
        await self.execute_sql(sql.get_sql(), phg)

        for i in when_complete:
            await i()

        return id_lst

    async def delete(self, info: QueryInfo, *, _perm=None) -> IDList:
        model = self.mapping2model[info.from_table]
        when_before_delete, when_complete = [], []
        await info.from_table.on_delete(info, when_before_delete, when_complete, _perm)

        qi = info.clone()
        qi.select = []
        lst = await self.get_list(qi)

        # 选择项
        id_lst = [x.id for x in lst]

        for i in when_before_delete:
            await i(id_lst)

        phg = self.get_placeholder_generator()
        sql = Query().from_(model).delete().where(model.id.isin(phg.next(id_lst)))
        await self.execute_sql(sql.get_sql(), phg)

        for i in when_complete:
            await i()

        return id_lst

    async def get_list(self, info: QueryInfo, with_count=False, *, _perm=None) -> List[QueryResultRow]:
        # hook
        await info.from_table.on_query(info)
        when_complete = []
        await info.from_table.on_read(info, when_complete, _perm)

        model = self.mapping2model[info.from_table]

        # 选择项
        q = Query()
        q = q.from_(model)

        select_fields = [model.id]
        for i in info.select_for_curd:
            select_fields.append(getattr(self.mapping2model[i.table], i))

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
                    field = getattr(self.mapping2model[c.column.table], c.column)

                    if isinstance(c.value, RecordMappingField):
                        real_value = getattr(self.mapping2model[c.value.table], c.value)
                    else:
                        real_value = phg.next(c.value)

                    cond = getattr(field, _sql_method_map[c.op])(real_value)
                    return cond

            if info.join:
                for ji in info.join:
                    jtable = self.mapping2model[ji.table]
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

        # 一些限制
        if info.order_by:
            q = q.orderby(info.order_by)
        if info.limit != -1:
            q = q.limit(info.limit)
        q = q.offset(info.offset)

        # 查询结果
        ret = []
        cursor = await self.execute_sql(q.get_sql(), phg)

        for i in cursor:
            it = iter(i)
            ret.append(QueryResultRow(next(it), list(it), info, info.from_table))

        for i in when_complete:
            await i(ret)

        return ret

    @abstractmethod
    def get_placeholder_generator(self) -> PlaceHolderGenerator:
        pass

    @abstractmethod
    async def execute_sql(self, sql, phg: PlaceHolderGenerator):
        pass

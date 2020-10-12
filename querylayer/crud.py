from abc import abstractmethod
from dataclasses import dataclass, field
from functools import reduce
from typing import Any, Union, Tuple, List, Type, Dict, Iterable

import pypika
from pypika import Query
from pypika.terms import ComplexCriterion

from querylayer.const import QUERY_OP_COMPARE, QUERY_OP_RELATION
from querylayer.query import QueryInfo, QueryConditions, ConditionExpr, QueryJoinInfo, ConditionLogicExpr
from querylayer.types import RecordMapping, RecordMappingField
from querylayer.utils.name_helper import get_class_full_name
from querylayer.values import ValuesToWrite

_sql_method_map = {
    # '+': '__pos__',
    # '-': '__neg__',
    QUERY_OP_COMPARE.EQ: '__eq__',
    QUERY_OP_COMPARE.NE: '__ne__',
    QUERY_OP_COMPARE.LT: '__lt__',
    QUERY_OP_COMPARE.LE: '__le__',
    QUERY_OP_COMPARE.GE: '__ge__',
    QUERY_OP_COMPARE.GT: '__gt__',
    QUERY_OP_RELATION.IN: 'isin',  # __lshift__ = _e(OP.IN)
    QUERY_OP_RELATION.NOT_IN: 'notin',
    QUERY_OP_RELATION.IS: '__eq__',  # __rshift__ = _e(OP.IS)
    QUERY_OP_RELATION.IS_NOT: '__ne__',
    QUERY_OP_RELATION.CONTAINS: 'contains',
    QUERY_OP_RELATION.CONTAINS_ANY: 'has_any_keys',
    QUERY_OP_RELATION.PREFIX: 'startswith',
}


@dataclass
class QueryResultRow:
    id: Any
    raw_data: Union[Tuple, List]
    info: QueryInfo

    base: Type[RecordMapping]
    extra: Any = field(default_factory=lambda: {})

    def to_data(self):
        data = {}
        for i, j in zip(self.info.select_for_curd, self.raw_data):
            if i.table == self.base:
                data[i] = j

        if self.extra:
            ex = {}
            for k, v in self.extra.items():
                if isinstance(v, List):
                    ex[k] = [x.to_dict() for x in v]
                elif isinstance(v, QueryResultRow):
                    ex[k] = v.to_dict()
                else:
                    ex[k] = None
            data['$extra'] = ex
        return data

    def to_dict(self):
        data = {}
        for i, j in zip(self.info.select_for_curd, self.raw_data):
            if i.table == self.base:
                data[i] = j

        if self.extra:
            ex = {}
            for k, v in self.extra.items():
                if isinstance(v, List):
                    ex[k] = [x.to_dict() for x in v]
                elif isinstance(v, QueryResultRow):
                    ex[k] = v.to_dict()
                else:
                    ex[k] = None
            data['$extra'] = ex
        return data

    def __repr__(self):
        return '<%s %s id: %s>' % (self.__class__.__name__, get_class_full_name(self.info.from_table), self.id)


@dataclass
class SQLCrud:
    mapping2model: Dict[Type[RecordMapping], pypika.Table]

    async def get_list_with_foreign_keys(self, info: QueryInfo):
        ret = await self.get_list(info)

        async def solve(ret_lst, main_table, fk_queries):
            pk_items = [x.id for x in ret_lst]

            for raw_name, query in fk_queries.items():
                query: QueryInfo
                limit = 0 if raw_name.endswith('[]') else 1

                # 上级ID，数据，查询条件
                q = QueryInfo(main_table, [query.from_table.id, *query.select])
                q.conditions = QueryConditions([ConditionExpr(info.from_table.id, QUERY_OP_RELATION.IN, pk_items)])
                q.join = [QueryJoinInfo(query.from_table, query.conditions, limit=limit)]

                elist = []
                for x in await self.get_list(q):
                    x.base = query.from_table
                    elist.append(x)

                extra: Dict[Any, Union[List, QueryResultRow]] = {}

                if limit != 1:
                    for x in elist:
                        extra.setdefault(x.id, [])
                        extra[x.id].append(x)
                else:
                    for x in elist:
                        extra[x.id] = x

                for i in ret_lst:
                    i.extra[raw_name] = extra.get(i.id)

                if query.foreign_keys:
                    await solve(elist, query.from_table, query.foreign_keys)

        await solve(ret, info.from_table, info.foreign_keys)
        return ret

    async def get_list(self, info: QueryInfo) -> List[QueryResultRow]:
        model = self.mapping2model[info.from_table]

        # 选择项
        q = Query()
        q = q.from_(model)

        select_fields = [model.id]
        for i in info.select_for_curd:
            select_fields.append(getattr(self.mapping2model[i.table], i))

        q = q.select(*select_fields)

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
                        real_value = c.value

                    cond = getattr(field, _sql_method_map[c.op])(real_value)
                    return cond

            ret = solve_condition(info.conditions)
            if ret:
                q = q.where(ret)

            if info.join:
                for ji in info.join:
                    jtable = self.mapping2model[ji.table]
                    where = solve_condition(ji.conditions)

                    if ji.limit == 0:
                        q = q.inner_join(jtable).on(where)
                    else:
                        q = q.inner_join(jtable).on(
                            jtable.id == Query.from_(jtable).select(jtable.id).where(where).limit(ji.limit)
                        )

        # 一些限制
        if info.order_by:
            q = q.orderby(info.order_by)
        q = q.limit(info.limit)
        q = q.offset(info.offset)

        # 查询结果
        ret = []
        cursor = await self.execute_sql(q.get_sql())

        for i in cursor:
            ret.append(QueryResultRow(i[0], i[1:], info, info.from_table))

        return ret

    async def delete(self, info: QueryInfo) -> int:
        model = self.mapping2model[info.from_table]
        qi = info.clone()
        qi.select = []
        lst = await self.get_list(qi)

        # 选择项
        sql = Query().from_(model).delete().where(model.id.isin([x.id for x in lst]))
        ret = await self.execute_sql(sql.get_sql())
        return ret.rowcount

    async def update(self, info: QueryInfo, values: ValuesToWrite, returning=False) -> Union[int, List[QueryResultRow]]:
        model = self.mapping2model[info.from_table]
        qi = info.clone()
        qi.select = []
        lst = await self.get_list(qi)

        # 选择项
        sql = Query().update(model).where(model.id.isin([x.id for x in lst]))
        for k, v in values.items():
            sql = sql.set(k, v)

        ret = await self.execute_sql(sql.get_sql())
        if returning:
            return await self.get_list(info)
        return ret.rowcount

    async def insert_many(self, table: Type[RecordMapping], values_list: Iterable[ValuesToWrite], returning=False)  -> Union[List[Any], List[QueryResultRow]]:
        model = self.mapping2model[table]

        sql_lst = []
        for i in values_list:
            sql = Query().into(model).columns(*i.keys()).insert(*i.values())
            sql_lst.append(sql)

        ret = []
        for i in sql_lst:
            ret.append(await self.execute_sql(i.get_sql()))

        if returning:
            qi = QueryInfo(table, [getattr(table, x) for x in table.__dataclass_fields__.keys()], conditions=QueryConditions([
                ConditionExpr(table.id, QUERY_OP_RELATION.IN, [x.lastrowid for x in ret]),
            ]))
            return await self.get_list(qi)
        return [x.lastrowid for x in ret]

    @abstractmethod
    async def execute_sql(self, sql):
        pass


@dataclass
class PeeweeCrud(SQLCrud):
    db: Any

    async def execute_sql(self, sql):
        return self.db.execute_sql(sql)

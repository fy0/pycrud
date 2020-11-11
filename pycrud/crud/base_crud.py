from abc import ABC
from dataclasses import dataclass
from typing import Any, Dict, Union, List, Type, Iterable

import pydantic

from pycrud.const import QUERY_OP_RELATION
from pycrud.crud._core_crud import CoreCrud
from pycrud.crud.query_result_row import QueryResultRow, QueryResultRowList
from pycrud.error import PermissionException, InvalidQueryValue
from pycrud.permission import RoleDefine, A
from pycrud.query import QueryInfo, QueryConditions, ConditionExpr, QueryJoinInfo, ConditionLogicExpr, UnaryExpr
from pycrud.types import RecordMapping, IDList, RecordMappingField
from pycrud.values import ValuesToWrite


@dataclass
class PermInfo:
    is_check: bool
    user: Any
    role: 'RoleDefine'

    def __bool__(self):
        return self.is_check


@dataclass
class BaseCrud(CoreCrud, ABC):
    permission: Any

    async def solve_returning(self, table: Type[RecordMapping], id_lst: IDList, info: QueryInfo = None,
                              perm: PermInfo = None):
        if info:
            selects = info.select_for_crud
        else:
            selects = [getattr(table, x) for x in table.__annotations__.keys()]

        qi = QueryInfo(table, selects, conditions=QueryConditions([
            ConditionExpr(table.id, QUERY_OP_RELATION.IN, id_lst),
        ]))

        if perm:
            return await self.get_list_with_perm(qi, perm=perm)
        else:
            return await self.get_list(qi, _perm=perm)

    @staticmethod
    async def _solve_query(info: QueryInfo, perm: PermInfo):
        if perm.is_check:
            allow_query = perm.role.get_perm_avail(info.from_table, A.QUERY)
            allow_read = perm.role.get_perm_avail(info.from_table, A.READ)

            def sub_solve_items(items):
                if items:
                    r = [solve_condition(x) for x in items if x is not None]
                    # solve_condition 返回值仍有 None 的可能
                    return [x for x in r if x is not None]
                return []

            def solve_condition(c):
                if isinstance(c, QueryConditions):
                    return QueryConditions(sub_solve_items(c.items))

                elif isinstance(c, ConditionLogicExpr):
                    items = sub_solve_items(c.items)
                    if items:
                        return ConditionLogicExpr(c.type, items)
                    return None

                elif isinstance(c, ConditionExpr):
                    if c.column not in allow_query:
                        # permission
                        return None

                    if isinstance(c.value, RecordMappingField):
                        if c.value not in allow_query:
                            # permission
                            return None

                    return c

                elif isinstance(c, UnaryExpr):
                    return c

            select_new = [x for x in info.select if x in allow_read]

            info.select = select_new
            info.conditions = solve_condition(info.conditions)

        return info

    async def insert_many_with_perm(self, table: Type[RecordMapping], values_list: Iterable[ValuesToWrite],
                                    returning=False, *, perm: PermInfo = None) -> Union[IDList, List[QueryResultRow]]:
        values_list_new = []

        if perm is None:
            perm = PermInfo(False, None, None)

        if perm.is_check:
            avail = perm.role.get_perm_avail(table, A.CREATE)

        for i in values_list:
            if perm.is_check:
                for j in (i.keys() - avail):
                    del i[j]

            try:
                i.bind(True, table=table)
                if i:
                    values_list_new.append(i)
            except pydantic.ValidationError as e:
                # TODO: 权限检查之后过不了检验的后面再处置
                raise e

        lst = await self.insert_many(table, values_list_new, _perm=perm)

        if returning:
            return await self.solve_returning(table, lst, perm=perm)

        return lst

    async def update_with_perm(self, info: QueryInfo, values: ValuesToWrite, returning=False,
                               *, perm: PermInfo = None) -> Union[List[Any], List[QueryResultRow]]:
        if perm is None:
            perm = PermInfo(False, None, None)

        if perm.is_check:
            avail = perm.role.get_perm_avail(info.from_table, A.UPDATE)
            rest = []

            for j in values.keys():
                if '.' in j:
                    j2, _ = j.split('.', 1)
                else:
                    j2 = j

                if j2 not in avail:
                    rest.append(j)

            for i in rest:
                del values[i]

        try:
            values.bind(False, table=info.from_table)
        except pydantic.ValidationError:
            # TODO: 权限检查之后过不了检验的后面再处置
            pass

        if not values:
            raise InvalidQueryValue('empty values')

        info = await self._solve_query(info, perm)
        lst = await self.update(info, values, _perm=perm)

        if returning:
            return await self.solve_returning(info.from_table, lst, info, perm=perm)

        return lst

    async def delete_with_perm(self, info: QueryInfo, *, perm: PermInfo=None) -> int:
        if perm is None:
            perm = PermInfo(False, None, None)
        if perm.is_check:
            if not perm.role.can_delete(info.from_table):
                raise PermissionException('delete', info.from_table)

        info = await self._solve_query(info, perm)
        return await self.delete(info, _perm=perm)

    async def get_list_with_perm(self, info: QueryInfo, with_count=False, *,
                                 perm: PermInfo = None) -> QueryResultRowList:
        if perm is None:
            perm = PermInfo(False, None, None)
        info = await self._solve_query(info, perm)
        return await self.get_list(info, with_count, _perm=perm)

    async def get_list_with_foreign_keys(self, info: QueryInfo, with_count=False,
                                         perm: PermInfo = None) -> QueryResultRowList:
        if perm is None:
            perm = PermInfo(False, None, None)

        ret = await self.get_list_with_perm(info, with_count, perm=perm)

        async def solve(ret_lst, main_table, fk_queries, depth=0):
            if fk_queries is None:
                return

            if depth == 0:
                pk_items = [x.id for x in ret_lst]
            else:
                pk_items = [x.raw_data[0] for x in ret_lst]

            for raw_name, query in fk_queries.items():
                query: QueryInfo
                limit = -1 if raw_name.endswith('[]') else 1

                # 上级ID，数据，查询条件
                q = QueryInfo(main_table, [query.from_table.id, *query.select])
                q.conditions = QueryConditions([ConditionExpr(main_table.id, QUERY_OP_RELATION.IN, pk_items)])
                q.join = [QueryJoinInfo(query.from_table, query.conditions, limit=limit)]

                elist = []
                for x in await self.get_list_with_perm(q, perm=perm):
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

                if depth == 0:
                    for i in ret_lst:
                        i.extra[raw_name] = extra.get(i.id)
                else:
                    for i in ret_lst:
                        i.extra[raw_name] = extra.get(i.raw_data[0])

                if query.foreign_keys:
                    await solve(elist, query.from_table, query.foreign_keys, depth + 1)

        await solve(ret, info.from_table, info.foreign_keys)
        return ret

from abc import ABC
from dataclasses import dataclass
from typing import Any, Dict, Union, List, Type, Iterable

from pycurd.const import QUERY_OP_RELATION
from pycurd.crud._core_crud import CoreCrud
from pycurd.crud.query_result_row import QueryResultRow
from pycurd.error import PermissionException
from pycurd.permission import RoleDefine, A
from pycurd.query import QueryInfo, QueryConditions, ConditionExpr, QueryJoinInfo, ConditionLogicExpr
from pycurd.types import RecordMapping, IDList, RecordMappingField
from pycurd.values import ValuesToWrite


@dataclass
class PermInfo:
    is_check: bool
    user: Any
    role: 'RoleDefine'


@dataclass
class BaseCrud(CoreCrud, ABC):
    permission: Any

    async def solve_returning(self, table: Type[RecordMapping], id_lst: IDList, info: QueryInfo = None,
                              perm: PermInfo = None):
        if info:
            selects = info.select_for_curd
        else:
            selects = [getattr(table, x) for x in table.__annotations__.keys()]

        qi = QueryInfo(table, selects, conditions=QueryConditions([
            ConditionExpr(table.id, QUERY_OP_RELATION.IN, id_lst),
        ]))

        if perm:
            return await self.get_list_with_perm(qi, perm=perm)
        else:
            return await self.get_list(qi)

    @staticmethod
    async def _solve_query(info: QueryInfo, perm: PermInfo):
        if perm.is_check:
            allow_query = perm.role.get_perm_avail(info.from_table, A.QUERY)
            allow_read = perm.role.get_perm_avail(info.from_table, A.READ)

            def sub_solve_items(items):
                if items:
                    return [solve_condition(x) for x in items if x is not None]
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

            select_new = [x for x in info.select if x in allow_read]

            info.select = select_new
            info.conditions = solve_condition(info.conditions)

        return info

    async def insert_many_with_perm(self, table: Type[RecordMapping], values_list: Iterable[ValuesToWrite],
                                    returning=False, *, perm: PermInfo) -> Union[IDList, List[QueryResultRow]]:
        if perm.is_check:
            values_list_new = []
            avail = perm.role.get_perm_avail(table, A.CREATE)

            for i in values_list:
                data = {k: v for k, v in i.items() if k in avail}
                if data:
                    values_list_new.append(data)
        else:
            values_list_new = values_list

        lst = await self.insert_many(table, values_list_new)

        if returning:
            return await self.solve_returning(table, lst, perm=perm)

        return lst

    async def update_with_perm(self, info: QueryInfo, values: ValuesToWrite, returning=False,
                               *, perm: PermInfo) -> Union[List[Any], List[QueryResultRow]]:
        if perm.is_check:
            avail = perm.role.get_perm_avail(info.from_table, A.WRITE)
            data = {k: v for k, v in values.items() if k in avail}
        else:
            data = values

        info = await self._solve_query(info, perm)
        lst = await self.update(info, data)

        if returning:
            return await self.solve_returning(info.from_table, lst, info, perm=perm)

        return lst

    async def delete_with_perm(self, info: QueryInfo, *, perm: PermInfo) -> int:
        if perm.is_check:
            if not perm.role.can_delete(info.from_table):
                raise PermissionException('delete', info.from_table)

        info = await self._solve_query(info, perm)
        return await self.delete(info)

    async def get_list_with_perm(self, info: QueryInfo, *, perm: PermInfo) -> List[QueryResultRow]:
        info = await self._solve_query(info, perm)
        return await self.get_list(info)

    async def get_list_with_foreign_keys(self, info: QueryInfo, perm: PermInfo = None):
        if perm is None:
            perm = PermInfo(False, None, None)

        ret = await self.get_list_with_perm(info, perm=perm)

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
                    await solve(elist, query.from_table, query.foreign_keys, depth+1)

        await solve(ret, info.from_table, info.foreign_keys)
        return ret

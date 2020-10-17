from abc import ABC
from dataclasses import dataclass
from typing import Any, Dict, Union, List, Type, Iterable

from querylayer.const import QUERY_OP_RELATION
from querylayer.crud._core_crud import CoreCrud
from querylayer.crud.query_result_row import QueryResultRow
from querylayer.error import PermissionException
from querylayer.permission import RolePerm, A
from querylayer.query import QueryInfo, QueryConditions, ConditionExpr, QueryJoinInfo, ConditionLogicExpr
from querylayer.types import RecordMapping, IDList, RecordMappingField
from querylayer.values import ValuesToWrite


@dataclass
class PermInfoForCrud:
    is_check: bool
    user: Any
    role: 'RolePerm'


@dataclass
class BaseCrud(CoreCrud, ABC):
    permission: Any

    async def solve_returning(self, table: Type[RecordMapping], id_lst: IDList, info: QueryInfo = None,
                              perm: PermInfoForCrud = None):
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
    async def _solve_query(info: QueryInfo, perm: PermInfoForCrud):
        if perm.is_check:
            allow_query = perm.role.get_perm_avail(info.from_table, A.QUERY)
            allow_read = perm.role.get_perm_avail(info.from_table, A.READ)

            def sub_solve_items(items):
                return [solve_condition(x) for x in items if x is not None]

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
                                    returning=False, *, perm: PermInfoForCrud) -> Union[IDList, List[QueryResultRow]]:
        if perm.is_check:
            values_list_new = []
            avail = perm.role.get_perm_avail(table, A.CREATE)

            for i in values_list:
                data = {k: v for k, v in i.items() if k in avail}
                values_list_new.append(data)
        else:
            values_list_new = values_list

        lst = await self.insert_many(table, values_list_new)

        if returning:
            return await self.solve_returning(table, lst, perm=perm)

        return lst

    async def update_with_perm(self, info: QueryInfo, values: ValuesToWrite, returning=False,
                               *, perm: PermInfoForCrud) -> Union[List[Any], List[QueryResultRow]]:
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

    async def delete_with_perm(self, info: QueryInfo, *, perm: PermInfoForCrud) -> int:
        if perm.is_check:
            if not perm.role.can_delete(info.from_table):
                raise PermissionException('delete', info.from_table)

        info = await self._solve_query(info, perm)
        return await self.delete(info)

    async def get_list_with_perm(self, info: QueryInfo, *, perm: PermInfoForCrud) -> List[QueryResultRow]:
        info = await self._solve_query(info, perm)
        return await self.get_list(info)

    async def get_list_with_foreign_keys(self, info: QueryInfo, perm: PermInfoForCrud = None):
        if perm is None:
            perm = PermInfoForCrud(False, None, None)

        ret = await self.get_list_with_perm(info, perm=perm)

        async def solve(ret_lst, main_table, fk_queries):
            if fk_queries is None:
                return
            pk_items = [x.id for x in ret_lst]

            for raw_name, query in fk_queries.items():
                query: QueryInfo
                limit = 0 if raw_name.endswith('[]') else 1

                # 上级ID，数据，查询条件
                q = QueryInfo(main_table, [query.from_table.id, *query.select])
                q.conditions = QueryConditions([ConditionExpr(info.from_table.id, QUERY_OP_RELATION.IN, pk_items)])
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

                for i in ret_lst:
                    i.extra[raw_name] = extra.get(i.id)

                if query.foreign_keys:
                    await solve(elist, query.from_table, query.foreign_keys)

        await solve(ret, info.from_table, info.foreign_keys)
        return ret

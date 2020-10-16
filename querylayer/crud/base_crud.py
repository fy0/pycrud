from abc import abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Union, List, Type, Iterable

from querylayer.const import QUERY_OP_RELATION
from querylayer.crud.query_result_row import QueryResultRow
from querylayer.query import QueryInfo, QueryConditions, ConditionExpr, QueryJoinInfo
from querylayer.types import RecordMapping
from querylayer.values import ValuesToWrite


@dataclass
class BaseCrud:
    permission: Any

    @abstractmethod
    async def insert_many(self, table: Type[RecordMapping], values_list: Iterable[ValuesToWrite],
                          returning=False, check_permission=True) -> Union[List[Any], List[QueryResultRow]]:
        pass

    @abstractmethod
    async def update(self, info: QueryInfo, values: ValuesToWrite, returning=False, check_permission=True) ->\
            Union[int, List[QueryResultRow]]:
        pass

    @abstractmethod
    async def delete(self, info: QueryInfo, check_permission=True) -> int:
        pass

    @abstractmethod
    async def get_list(self, info: QueryInfo, check_permission=True) -> List[QueryResultRow]:
        pass

    async def get_list_with_foreign_keys(self, info: QueryInfo, check_permission=True):
        ret = await self.get_list(info, check_permission=check_permission)

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
                for x in await self.get_list(q, check_permission=check_permission):
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

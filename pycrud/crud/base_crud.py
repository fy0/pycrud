from abc import ABC
from typing import Any, Dict, Union, List, Type, Iterable

import pydantic

from pycrud.const import QUERY_OP_RELATION
from pycrud.crud._core_crud import CoreCrud
from pycrud.crud.query_result_row import QueryResultRow, QueryResultRowList
from pycrud.error import PermissionException, InvalidQueryValue
from pycrud.permission import RoleDefine, A, PermInfo, TablePerm
from pycrud.query import QueryInfo, QueryConditions, ConditionExpr, QueryJoinInfo, ConditionLogicExpr, UnaryExpr
from pycrud.types import Entity, IDList, EntityField
from pycrud.values import ValuesToUpdate, ValuesToCreate


class BaseCrud(CoreCrud, ABC):
    permission: Dict[str, RoleDefine] = {}
    _permission_list: List[RoleDefine]

    default_role: RoleDefine = None

    def __init__(self, permission: List[RoleDefine]):
        self._permission_list = permission

    def permission_apply(self):
        self.permission.clear()

        permission_list = []
        if not self._permission_list:
            data = {}
            entity2model = getattr(self, 'entity2model', None)
            if entity2model:
                entities: List[Type[Entity]] = entity2model.keys()
                for i in entities:
                    data[i] = TablePerm({}, default_perm={A.QUERY, A.CREATE, A.READ, A.UPDATE}, allow_delete=True)

            permission_list.append(RoleDefine('visitor', data))
        else:
            permission_list = self._permission_list
            assert len(permission_list), 'must define one role at least'

        self.default_role = permission_list[0]

        for i in permission_list:
            self.permission[i.name] = i
        for i in permission_list:
            if isinstance(i.based_on, str):
                role = self.permission.get(i.based_on, None)
                assert role is not None, f"Can't find the role `{i.based_on}` which is `{i.name}` based on"
                i.based_on = role
        for i in permission_list:
            i.bind()

    def __post_init__(self):
        self.permission_apply()

    async def solve_returning(self, table: Type[Entity], id_lst: IDList, info: QueryInfo = None,
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
        if perm:
            allow_query = perm.role.get_perm_avail(info.table, A.QUERY)
            allow_read = perm.role.get_perm_avail(info.table, A.READ)

            if info.join:
                allow_query = set(allow_query)
                allow_read = set(allow_read)

                for i in info.join:
                    allow_query.update(perm.role.get_perm_avail(i.table, A.QUERY))
                    allow_read.update(perm.role.get_perm_avail(i.table, A.READ))

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

                    if isinstance(c.value, EntityField):
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

    async def insert_many_with_perm(self, entity: Type[Entity], values_list: Iterable[ValuesToCreate],
                                    returning=False, *, perm: PermInfo = None) -> Union[IDList, List[QueryResultRow]]:
        values_list_new = []

        if perm is None:
            perm = PermInfo()
        perm._init(self)

        if perm:
            avail = perm.role.get_perm_avail(entity, A.CREATE)

        for i in values_list:
            if perm:
                for j in (i.keys() - avail):
                    del i[j]

            try:
                i.bind(entity)
                if i:
                    values_list_new.append(i)
            except pydantic.ValidationError as e:
                # TODO: 权限检查之后过不了检验的后面再处置
                raise e

        lst = await self.insert_many(entity, values_list_new, _perm=perm)

        if returning:
            return await self.solve_returning(entity, lst, perm=perm)

        return lst

    async def update_with_perm(self, info: QueryInfo, values: ValuesToUpdate, returning=False,
                               *, perm: PermInfo = None) -> Union[List[Any], List[QueryResultRow]]:
        if perm is None:
            perm = PermInfo()
        perm._init(self)

        if perm:
            avail = perm.role.get_perm_avail(info.table, A.UPDATE)
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
            values.bind(info.entity)
        except pydantic.ValidationError:
            # TODO: 权限检查之后过不了检验的后面再处置
            pass

        if not values:
            raise InvalidQueryValue('empty values')

        info = await self._solve_query(info, perm)
        lst = await self.update(info, values, _perm=perm)

        if returning:
            return await self.solve_returning(info.table, lst, info, perm=perm)

        return lst

    async def delete_with_perm(self, info: QueryInfo, *, perm: PermInfo = None) -> IDList:
        if perm is None:
            perm = PermInfo()
        perm._init(self)

        if perm and not perm.role.can_delete(info.table):
            raise PermissionException('delete', info.table)

        info = await self._solve_query(info, perm)
        return await self.delete(info, _perm=perm)

    async def get_list_with_perm(self, info: QueryInfo, with_count=False, *,
                                 perm: PermInfo = None) -> QueryResultRowList:
        if perm is None:
            perm = PermInfo()
        perm._init(self)
        info = await self._solve_query(info, perm)
        return await self.get_list(info, with_count, _perm=perm)

    async def get_list_with_foreign_keys(self, info: QueryInfo, with_count=False,
                                         perm: PermInfo = None) -> QueryResultRowList:
        if perm is None:
            perm = PermInfo()
        perm._init(self)

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
                q = QueryInfo(main_table, [query.entity.id, *query.select])
                q.conditions = QueryConditions([ConditionExpr(main_table.id, QUERY_OP_RELATION.IN, pk_items)])
                q.join = [QueryJoinInfo(query.entity, query.conditions, limit=limit)]

                elist = []
                for x in await self.get_list_with_perm(q, perm=perm):
                    x.base = query.entity
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
                    await solve(elist, query.entity, query.foreign_keys, depth + 1)

        await solve(ret, info.entity, info.foreign_keys)
        return ret

import copy
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Tuple, Any, TYPE_CHECKING, Optional, List, Set, Iterable, Union, Sequence, Type, Callable

from typing_extensions import Literal

from pycrud.utils import UserObject

if TYPE_CHECKING:
    from pycrud.types import EntityField, Entity
    from pycrud.crud.base_crud import BaseCrud

logger = logging.getLogger(__name__)


class A(Enum):
    QUERY = 'query'
    CREATE = 'create'
    READ = 'read'
    UPDATE = 'update'


#ALL = {A.QUERY, A.CREATE, A.READ, A.UPDATE}


class Sentinel:
    def __init__(self, val):
        self.val = val

    def __eq__(self, other):
        return self.val == other.val

    def __hash__(self):
        return hash(self.val)

# PermissionDesc = Dict[Type['RecordMapping'], Dict[Union[Any, Literal['*', '|']], set]]
PermissionDesc = Dict[Type['Entity'], 'TablePerm']
ALLOW_DELETE = Sentinel('aabb')


@dataclass
class RoleDefine:
    name: str
    permission_desc: PermissionDesc
    based_on: Union['RoleDefine', str] = None

    def __post_init__(self):
        pass

    def __hash__(self):
        return id(self)

    def bind(self):
        self._ability_table: Dict[Type['Entity'], Dict[Union[A, ALLOW_DELETE], Set['EntityField']]] = {}
        # self._table_type: Optional[Type['RecordMapping']] = None

        if self.based_on:
            assert isinstance(self.based_on, RoleDefine), 'based_on must be RoleDefine'
            self._ability_table = copy.deepcopy(self.based_on._ability_table)

        def solve_data(table: Type['Entity'], table_perm: TablePerm) -> Dict[str, Set[A]]:
            """
            整合默认值和叠加值，生成一份权限数据
            :param table:
            :param table_perm:
            :return:
            """
            if not (table_perm.default_perm or table_perm.append_perm):
                return table_perm.data

            tmp = {}
            # apply default
            if table_perm.default_perm:
                for i in table.record_fields.keys():
                    tmp[i] = table_perm.default_perm

            # apply current data
            for k, v in table_perm.data.items():
                tmp[k] = v

            # apply append
            if table_perm.append_perm:
                for i in table.record_fields:
                    if i in tmp:
                        s = tmp[i].copy()
                        s.update(table_perm.append_perm)
                    else:
                        s = table_perm.append_perm
                    tmp[i] = s

            return tmp

        for k, v in self.permission_desc.items():
            k: Type['Entity']
            v: TablePerm

            table_columns_by_ability = self._ability_table.get(k, {})
            table_columns_by_ability[ALLOW_DELETE] = v.allow_delete

            for column, abilities in solve_data(k, v).items():
                for a in abilities:
                    table_columns_by_ability.setdefault(a, set())
                    table_columns_by_ability[a].add(column)

            self._ability_table[k] = table_columns_by_ability

    def get_perm_avail(self, table: Type['Entity'], ability: A) -> Set['EntityField']:
        t = self._ability_table.get(table)
        if t:
            return t.get(ability, set())
        return set()

    def can_delete(self, table: Type['Entity']) -> bool:
        t = self._ability_table.get(table)
        return t[ALLOW_DELETE] if t else False


@dataclass
class TablePerm:
    data: Dict[Union[Any, Literal['*', '|']], set]
    default_perm: set = None
    append_perm: set = None

    allow_delete: bool = False


class AbilityTable:
    def __init__(self, name):
        self.table = name

    def __eq__(self, other):
        return self.table == other.model

    def __repr__(self):
        return '<Table %r>' % self.table


class AbilityColumn:
    def __init__(self, table, column):
        self.table = table
        self.column = column

    def __eq__(self, other):
        return self.table == other.model and self.column == other.column

    def __ne__(self, other):
        return self.table != other.model or self.column != other.column

    def __repr__(self):
        return '<Column %r.%r>' % (self.table, self.column)


class PermInfo:
    user: UserObject
    role: RoleDefine
    extra: Any

    def __init__(self, user: UserObject = None, role: Union['RoleDefine', str] = None, extra: Any = None, *, skip_check=False):
        self.user = user

        if isinstance(role, str):
            self.role = None
            self._role_str = role
        else:
            self.role = role
            self._role_str = None

        self.extra = extra
        self.skip_check = skip_check

    def __bool__(self):
        return not self.skip_check

    def _init(self, crud: 'BaseCrud'):
        if not self.role:
            # 绑定 role define
            if self._role_str is not None:
                # 文本则取对应
                self.role = crud.permission.get(self._role_str, None)
                assert self.role, 'role not found by name: %s' % self._role_str
            else:
                # 传空则取默认
                self.role = crud.default_role

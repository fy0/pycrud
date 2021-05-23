import functools
import inspect
from typing import Type, Union, List, Any, TYPE_CHECKING, Iterable, Set, Literal

from pydantic import constr
from pydantic.main import BaseModel, create_model

from pycrud.const import OP_QUERY_TYPE_1, OP_QUERY_TYPE_ARRAY, OP_QUERY_TYPE_STRING_LIKE, \
    OP_QUERY_TYPE_2, OP_UPDATE
from pycrud.helpers.pydantic_ext import DictWithKVPair, KVPair, HttpKVPair
from pycrud.permission import RoleDefine, A
from pycrud.utils import sentinel

if TYPE_CHECKING:
    from pycrud.types import Entity

try:
    from typing import get_origin
except ImportError:
    from typing_extensions import get_origin


class _DocBaseModel(BaseModel):
    @classmethod
    def validate(cls: Type['Model'], value: Any) -> 'Model':
        """ _DocBaseModel is not for data validation  """
        return value


def op_solve(op_set):
    ops = []
    for k in op_set:
        ops.extend(k.value)
    return '|'.join(ops)


def cache(func):
    @functools.wraps(func)
    def inner(self, *args, **kwargs):
        key = func.__name__, kwargs.get('role', None), kwargs.get('from_http_query', None)
        cache = self._cache.get(key)
        if not cache:
            cache = func(self, *args, **kwargs)
            self._cache[key] = cache

        return cache
    return inner


class DTOGenerator:
    def __init__(self, parent: Type['Entity']):
        self.parent = parent
        self._cache = {}

    @property
    def id_type(self):
        return self._get_parent_annotations().get('id', Any)

    @cache
    def _get_parent_annotations(self):
        cls = self.parent
        all_an = {}
        for i in inspect.getmro(cls)[::-1]:
            an = getattr(i, '__annotations__', None)
            if an:
                all_an.update(an)
        return {k: v for k, v in all_an.items() if k in cls.__fields__}

    def _get_perm_avail(self, role: str, ability: A) -> Union[Set[A], Literal[sentinel]]:
        if role is sentinel:
            return sentinel

        if self.parent.crud:
            p = self.parent.crud.permission
            role: RoleDefine = p.get(role)
            if role:
                return {str(x) for x in role.get_perm_avail(self.parent, ability)}
            return set()  # empty
        return sentinel  # default

    @cache
    def get_query_for_doc(self, role=sentinel) -> Type[BaseModel]:
        avail = self._get_perm_avail(role, A.READ)
        all_an = self._get_parent_annotations()

        fields = {}
        for name, v in all_an.items():
            if avail is not sentinel:
                if name not in avail: continue
            fields[f'{name}.{{op}}'] = (Union[v, List[v]], None)

        # 注：create_model 创建出来的Model的__init__参数不一样，所以不能被fastapi自动识别
        return create_model(
            '*dto_doc_query_' + self.parent.__name__,
            __base__=_DocBaseModel,
            **fields
        )

    @cache
    def get_query(self, role=sentinel, *, from_http_query=False) -> Type[BaseModel]:
        avail = self._get_perm_avail(role, A.READ)
        cls = self.parent
        all_an = self._get_parent_annotations()

        op_regex_common = op_solve(OP_QUERY_TYPE_1)
        op_regex_common2 = op_solve(OP_QUERY_TYPE_2)
        op_regex_array = op_solve(OP_QUERY_TYPE_ARRAY)
        op_regex_string_like = op_solve(OP_QUERY_TYPE_STRING_LIKE)
        tail = r'(\.\d+)?'

        unions = []
        KVPairCls = HttpKVPair if from_http_query else KVPair

        for name, v in all_an.items():
            if avail is not sentinel:
                if name not in avail: continue
            pairs = [
                KVPairCls[constr(regex=fr'^{name}\.({op_regex_common}){tail}$'), v],
                KVPairCls[constr(regex=fr'^{name}\.({op_regex_common2}){tail}?$'), List[v]],
            ]
            vorg = get_origin(v)
            if inspect.isclass(vorg):
                if issubclass(vorg, Iterable):
                    pairs.append(KVPair[constr(regex=fr'^{name}\.({op_regex_array}){tail}$'), v])
                elif issubclass(vorg, (str, bytes,)):
                    pairs.append(KVPair[constr(regex=fr'^{name}\.({op_regex_string_like}){tail}$'), v])
            unions.extend(pairs)

        return create_model(
            '*dto_query_' + cls.__name__,
            __base__=BaseModel,
            __root__=(DictWithKVPair[Union[tuple(unions)]], None),
        )

    @cache
    def get_create(self, role=sentinel) -> Type[BaseModel]:
        avail = self._get_perm_avail(role, A.CREATE)
        return self.parent.clone(prefix='*dto_create_', fields=avail, base_cls=BaseModel)

    @cache
    def get_read(self, role=sentinel) -> Type[BaseModel]:
        avail = self._get_perm_avail(role, A.READ)
        return self.parent.clone(prefix='*dto_read_', fields=avail, base_cls=BaseModel)

    @cache
    def get_update_v2(self, role=sentinel) -> Type[BaseModel]:
        avail = self._get_perm_avail(role, A.UPDATE)
        cls = self.parent
        all_an = self._get_parent_annotations()

        op_regex_num = op_solve([OP_UPDATE.INCR, OP_UPDATE.DECR])
        op_regex_array = op_solve([OP_UPDATE.ARRAY_EXTEND, OP_UPDATE.ARRAY_PRUNE,
                                   OP_UPDATE.ARRAY_EXTEND_DISTINCT, OP_UPDATE.ARRAY_PRUNE_DISTINCT])

        unions = []

        for name, v in all_an.items():
            if avail is not sentinel:
                if name not in avail: continue
            pairs = [
                KVPair[constr(regex=fr'^{name}$'), v],
            ]
            vorg = get_origin(v)
            if inspect.isclass(vorg):
                if issubclass(vorg, Iterable):
                    pairs.append(KVPair[constr(regex=fr'^{name}\.({op_regex_array})$'), v])
                elif issubclass(vorg, (int, float,)):
                    pairs.append(KVPair[constr(regex=fr'^{name}\.({op_regex_num})$'), v])
            unions.extend(pairs)

        return create_model(
            '*dto_update_' + cls.__name__,
            __base__=BaseModel,
            __root__=(DictWithKVPair[Union[tuple(unions)]], None),
        )

    @cache
    def get_update(self, role=sentinel) -> Type[BaseModel]:
        avail = self._get_perm_avail(role, A.UPDATE)
        cls = self.parent
        all_an = self._get_parent_annotations()

        fields = {}

        for name, v in all_an.items():
            if avail is not sentinel:
                if name not in avail: continue

            fields[name] = (v, None)

            vorg = get_origin(v)
            if inspect.isclass(vorg):
                if issubclass(vorg, Iterable):
                    for i in [OP_UPDATE.ARRAY_EXTEND, OP_UPDATE.ARRAY_PRUNE,
                                   OP_UPDATE.ARRAY_EXTEND_DISTINCT, OP_UPDATE.ARRAY_PRUNE_DISTINCT]:
                        for op in i.value:
                            fields[f'{name}.{op}'] = (v, None)
                elif issubclass(vorg, (int, float,)):
                    fields[name + '.incr'] = (v, None)
                    fields[name + '.desc'] = (v, None)

        assert len(fields), f'角色 {role} 对 {self.parent.__name__} 所有列均无 update 权限，永远无法通过校验'

        return create_model(
            '*dto_update_' + cls.__name__,
            __base__=BaseModel,
            **fields
        )

    @cache
    def resp_create(self, role=sentinel):
        cls = self.parent
        model = self.get_read(role)
        return create_model(
            '*dto_resp_create_' + cls.__name__,
            __base__=BaseModel,
            __root__=(Union[List[self.id_type], List[model]], None)
        )

    @cache
    def resp_update(self, role=sentinel):
        cls = self.parent
        model = self.get_read(role)
        return create_model(
            '*dto_resp_upadte_' + cls.__name__,
            __base__=BaseModel,
            __root__=(Union[List[self.id_type], List[model]], None)
        )

    @cache
    def resp_delete(self, role=sentinel):
        cls = self.parent
        return create_model(
            '*dto_resp_delete_' + cls.__name__,
            __base__=BaseModel,
            __root__=(List[self.id_type], None)
        )

    @cache
    def resp_list(self, role=sentinel):
        cls = self.parent
        model = self.get_read(role)
        return create_model(
            '*dto_resp_list_' + cls.__name__,
            __base__=BaseModel,
            __root__=(List[model], None)
        )

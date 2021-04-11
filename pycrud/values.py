from enum import Enum
from typing import Mapping, TYPE_CHECKING, Type, Dict, Union

from multidict import MultiDict

from pycrud.error import InvalidQueryConditionValue, InvalidQueryValue

if TYPE_CHECKING:
    from pycrud.types import Entity


def _dict_convert(data: Union[Dict, MultiDict]) -> Dict:
    """
    Convert Dict and MultiDict to Dict
    :param data:
    :return:
    """
    if isinstance(data, MultiDict):
        data = MultiDict(data)
        tmp = {}

        for k, v in data.items():
            # 提交多个相同值，等价于提交一个数组（用于formdata和urlencode形式）
            v_all = data.getall(k)
            if len(v_all) > 1:
                v = v_all
            tmp[k] = v

        return tmp
    elif isinstance(data, dict):
        return data
    else:
        return dict(data)


class _ValuesToWrite(dict):
    def __init__(self, data: Union[Dict, MultiDict] = None, entity: Type['Entity'] = None):
        super().__init__()

        self.entity = entity
        self.is_bind = False

        if data:
            self.clear()
            self.update(_dict_convert(data))

    def _bind(self, entity=None):
        entity = entity or self.entity
        final = {}

        # skip keys startswith '$'
        for k, v in self.items():
            if k.startswith('$'):
                continue
            final[k] = v

        # parse
        ret = entity.parse_obj(final)
        self.clear()
        self.update(ret.dict(exclude_unset=False, exclude_none=True))
        return self


class ValuesToCreate(_ValuesToWrite):
    """
    Class to store create values
    """

    def __init__(self, data: Union[Dict, MultiDict, 'Entity'] = None, entity: Type['Entity'] = None):
        from pycrud.types import Entity

        # check if data is an Entity
        if data and isinstance(data, Entity):
            if not entity:
                entity = type(data)

            data = data.dict(include=data.__fields_set__)

        super().__init__(data, entity)

    def bind(self, entity: Type['Entity'] = None, force=False):
        """
        parse values
        :param entity: Entity class to overwrite
        :param force:
        :return:
        """
        if self.is_bind and (not force):
            return self

        return super()._bind(entity)


class ValuesDataUpdateFlag(Enum):
    INCR = 'incr'
    DECR = 'decr'

    ARRAY_EXTEND = 'array_extend'
    ARRAY_PRUNE = 'array_prune'

    ARRAY_EXTEND_DISTINCT = 'array_extend_distinct'
    ARRAY_PRUNE_DISTINCT = 'array_prune_distinct'


class ValuesToUpdate(_ValuesToWrite):
    """
    Class to store update values
    """

    def __init__(self, data: Union[Dict, MultiDict, 'Entity'] = None, entity: Type['Entity'] = None):
        """
        Examples:
        ValuesToUpdate(UserEntity({'name': 'John'}))

        ValuesToUpdate({'name': 'John'}, UserEntity)

        ValuesToUpdate({'name': 'John', 'count.incr': 1}, UserEntity)

        v = ValuesToUpdate({'name': 'John'})
        v.bind(UserEntity)

        v = ValuesToUpdate(MultiDict({'name': 'John'}))
        v.bind(UserEntity)

        :param data:
        :param entity:
        """
        from pycrud.types import Entity

        # check if data is an Entity
        if data and isinstance(data, Entity):
            if not entity:
                entity = type(data)

            data = data.dict(include=data.__fields_set__)

        super().__init__(data, entity)
        self.data_flag: Dict[str, ValuesDataUpdateFlag] = {}

    def bind(self, entity: Type['Entity'] = None, force=False):
        """
        parse values
        :param entity: Entity class to overwrite
        :param force:
        :return:
        """
        if self.is_bind and (not force):
            return self

        entity = entity or self.entity
        final = {}

        # skip keys startswith '$'
        for k, v in self.items():
            if k.startswith('$'):
                continue
            final[k] = v

        final2 = {}

        for k, v in final.items():
            if '.' in k:
                _k, op = k.rsplit('.', 1)
                if _k in final:
                    raise Exception('duplicated keys: %r, %r' % (k, _k))
                if _k in self.data_flag:
                    raise Exception('duplicated keys: %r, %r' % (k, f'{_k}.{self.data_flag[_k]}'))

                flag = ValuesDataUpdateFlag._value2member_map_.get(op)
                if flag:
                    self.data_flag[_k] = flag
                else:
                    raise InvalidQueryConditionValue('unknown unary operator: %s' % k)

                k = _k

            final2[k] = v

        ret = entity.partial_model.parse_obj(final2)
        self.clear()
        self.update(ret.dict(include=ret.__fields_set__))

        self.is_bind = True
        return self


'''
def try_bind(self, entity=None):
    """
    试图进行绑定，但不进行过滤（只检查值类型）
    :param entity:
    :return:
    """
    bak = self.copy()
    self._bind(entity=entity)
    for i in bak.keys() - self.keys():
        if '.' in i:
            a, b = i.split('.', 1)
            if a in self:
                continue
        self[i] = bak[i]
    return self
'''

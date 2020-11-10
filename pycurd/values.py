from enum import Enum
from typing import Mapping, TYPE_CHECKING, Type, Dict

from multidict import MultiDict

from pycurd.error import InvalidQueryConditionValue, InvalidQueryValue

if TYPE_CHECKING:
    from pycurd.types import RecordMapping


class ValuesDataFlag(Enum):
    INCR = 'incr'
    DECR = 'decr'

    ARRAY_EXTEND = 'array_extend'
    ARRAY_PRUNE = 'array_prune'

    ARRAY_EXTEND_DISTINCT = 'array_extend_distinct'
    ARRAY_PRUNE_DISTINCT = 'array_prune_distinct'


class ValuesToWrite(dict):
    def __init__(self, raw_data=None, table: Type['RecordMapping'] = None, try_parse=False):
        super().__init__()
        self.table = table

        self.data_flag: Dict[str, ValuesDataFlag] = {}

        if raw_data:
            assert isinstance(raw_data, Mapping)

            self.clear()
            self.update(self._dict_convert(raw_data))

            if try_parse:
                self.try_bind()

    def _dict_convert(self, data) -> Dict:
        if isinstance(data, dict):
            return data

        elif isinstance(data, MultiDict):
            data = MultiDict(data)
            tmp = {}

            for k, v in data.items():
                # 提交多个相同值，等价于提交一个数组（用于formdata和urlencode形式）
                v_all = data.getall(k)
                if len(v_all) > 1:
                    v = v_all
                tmp[k] = v

            return tmp
        else:
            return dict(data)

    def try_bind(self, table=None):
        """
        试图进行绑定，但不进行过滤（只检查值类型）
        :param table:
        :return:
        """
        bak = self.copy()
        self.bind(check_insert=False, table=table)
        for i in bak.keys() - self.keys():
            if '.' in i:
                a, b = i.split('.', 1)
                if a in self:
                    continue
            self[i] = bak[i]
        return self

    def bind(self, check_insert=False, table=None):
        table = table or self.table
        final = {}

        for k, v in self.items():
            if k.startswith('$'):
                continue
            final[k] = v

        if check_insert:
            ret = table.parse_obj(final)
            self.clear()
            self.update(ret.dict(exclude_unset=False, exclude_none=True))
        else:
            final2 = {}

            for k, v in final.items():
                if '.' in k:
                    _k, op = k.rsplit('.', 1)
                    if _k in final:
                        raise Exception('duplicated keys: %r, %r' % (k, _k))
                    if _k in self.data_flag:
                        raise Exception('duplicated keys: %r, %r' % (k, f'{_k}.{self.data_flag[_k]}'))

                    flag = ValuesDataFlag._value2member_map_.get(op)
                    if flag:
                        self.data_flag[_k] = flag
                    else:
                        raise InvalidQueryConditionValue('unknown unary operator: %s' % k)

                    k = _k

                final2[k] = v

            ret = table.partial_model.parse_obj(final2)
            self.clear()
            self.update(ret.dict(include=ret.__fields_set__))

        return self

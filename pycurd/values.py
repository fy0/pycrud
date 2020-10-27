from typing import Mapping, TYPE_CHECKING, Type, Dict

from multidict import MultiDict

if TYPE_CHECKING:
    from pycurd.types import RecordMapping


class ValuesToWrite(dict):
    def __init__(self, raw_data=None, table: Type['RecordMapping'] = None, try_parse=False):
        super().__init__()
        self.table = table

        # design of incr/desc:
        # 1. incr/desc/normal_set can't be appear in the same time
        # 2. incr/desc use self to store data
        self.incr_fields = set()
        self.decr_fields = set()
        self.set_add_fields = set()
        self.set_remove_fields = set()
        self.array_append = set()
        self.array_remove = set()

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
        table = table or self.table
        ret = table.partial_model.parse_obj(self)

        for i in ret.__fields_set__:
            self[i] = getattr(ret, i)

        return self

    def bind(self, check_insert=False, table=None):
        table = table or self.table
        final = {}

        for k, v in self.items():
            if k.startswith('$'):
                continue
            elif '.' in k:
                # TODO: 不允许 incr 和普通赋值同时出现
                k, op = k.rsplit('.', 1)
                if op == 'incr':
                    self.incr_fields.add(k)
                elif op == 'decr':
                    self.decr_fields.add(k)
                elif op == 'set_add':
                    self.set_add_fields.add(k)
                elif op == 'set_remove':
                    self.set_remove_fields.add(k)
                # elif op == 'array_append':
                #     self.array_append.add(k)
                # elif op == 'array_remove':
                #    self.array_remove.add(k)

            final[k] = v

        if check_insert:
            ret = table.parse_obj(final)
            self.clear()
            self.update(ret.dict(exclude_unset=False, exclude_none=True))
        else:
            ret = table.partial_model.parse_obj(final)
            self.clear()
            self.update(ret.dict(include=ret.__fields_set__))

        return self

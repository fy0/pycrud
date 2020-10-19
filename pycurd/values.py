from typing import Mapping, TYPE_CHECKING, Type

from multidict import MultiDict

if TYPE_CHECKING:
    from pycurd.types import RecordMapping


class ValuesToWrite(dict):
    def __init__(self, table: Type['RecordMapping'], raw_data=None, check_insert=False):
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
            self.parse(raw_data, check_insert=check_insert)

    def parse(self, post_data: Mapping, check_insert=False):
        if isinstance(post_data, dict):
            post_data = MultiDict(post_data)

        tmp = {}

        for k, v in post_data.items():
            # 提交多个相同值，等价于提交一个数组（用于formdata和urlencode形式）
            v_all = post_data.getall(k)
            if len(v_all) > 1:
                v = v_all

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

            tmp[k] = v

        if check_insert:
            ret = self.table.parse_obj(tmp)

            self.clear()
            for i in ret.__fields__:
                self[i] = getattr(ret, i)
        else:
            ret = self.table.partial_model.parse_obj(tmp)

            self.clear()
            for i in ret.__fields_set__:
                self[i] = getattr(ret, i)

        return self

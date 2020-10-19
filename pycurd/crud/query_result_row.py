from dataclasses import dataclass, field
from typing import Any, Union, Tuple, List, Type

from pycurd.query import QueryInfo
from pycurd.types import RecordMapping
from pycurd.utils.name_helper import get_class_full_name


@dataclass
class QueryResultRow:
    id: Any
    raw_data: Union[Tuple, List]
    info: QueryInfo

    base: Type[RecordMapping]
    extra: Any = field(default_factory=lambda: {})

    def to_dict(self):
        data = {}
        for i, j in zip(self.info.select_for_curd, self.raw_data):
            if i.table == self.base:
                data[i] = j

        if self.extra:
            ex = {}
            for k, v in self.extra.items():
                if isinstance(v, List):
                    ex[k] = [x.to_dict() for x in v]
                elif isinstance(v, QueryResultRow):
                    ex[k] = v.to_dict()
                else:
                    ex[k] = None
            data['$extra'] = ex
        return data

    def __repr__(self):
        return '<%s %s id: %s>' % (self.__class__.__name__, get_class_full_name(self.info.from_table), self.id)

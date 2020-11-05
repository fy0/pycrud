from dataclasses import dataclass, field
from typing import Any, Union, Tuple, List, Type, TYPE_CHECKING

from pycurd.utils.name_helper import get_class_full_name

if TYPE_CHECKING:
    from pycurd.query import QueryInfo
    from pycurd.types import RecordMapping


@dataclass
class QueryResultRow:
    id: Any
    raw_data: Union[Tuple, List]
    info: 'QueryInfo'

    base: Type['RecordMapping']
    extra: Any = field(default_factory=lambda: {})

    def __post_init__(self):
        self._dict_cache = None

    def to_dict(self):
        if self._dict_cache is None:
            data = {}
            for i, j in zip(self.info.select_for_curd, self.raw_data):
                if i.table == self.base:
                    data[i.name] = j

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
            self._dict_cache = data

        return self._dict_cache

    def __repr__(self):
        return '<%s %s id: %s>' % (self.__class__.__name__, get_class_full_name(self.info.from_table), self.id)


class QueryResultRowList(list):
    def __init__(self, *args):
        super().__init__(*args)
        self.rows_count = None

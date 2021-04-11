from dataclasses import dataclass, field
from typing import Any, Union, Tuple, List, Type, TYPE_CHECKING

from pycrud.utils.name_helper import get_class_full_name

if TYPE_CHECKING:
    from pycrud.query import QueryInfo
    from pycrud.types import Entity


@dataclass
class QueryResultRow:
    id: Any
    raw_data: Union[Tuple, List]
    info: 'QueryInfo'

    base: Type['Entity']
    extra: Any = field(default_factory=lambda: {})

    def __post_init__(self):
        self._dict_cache = None

    def to_dict(self):
        if self._dict_cache is None:
            data = {}
            for i, j in zip(self.info.select_for_crud, self.raw_data):
                if i.entity == self.base:
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
        return '<%s %s id: %s>' % (self.__class__.__name__, get_class_full_name(self.info.table), self.id)


class QueryResultRowList(List[QueryResultRow]):
    def __init__(self, *args):
        super().__init__(*args)
        self.rows_count = None

from abc import abstractmethod
from dataclasses import dataclass
from typing import Type, Iterable, List

from pycrud.crud.query_result_row import QueryResultRow, QueryResultRowList
from pycrud.query import QueryInfo
from pycrud.types import RecordMapping, IDList
from pycrud.values import ValuesToWrite


@dataclass
class CoreCrud:
    @abstractmethod
    async def insert_many(self, table: Type[RecordMapping], values_list: Iterable[ValuesToWrite], *, _perm=None) -> IDList:
        pass

    @abstractmethod
    async def update(self, info: QueryInfo, values: ValuesToWrite, *, _perm=None) -> IDList:
        pass

    @abstractmethod
    async def delete(self, info: QueryInfo, *, _perm=None) -> int:
        pass

    @abstractmethod
    async def get_list(self, info: QueryInfo, with_count=False, *, _perm=None) -> QueryResultRowList:
        pass

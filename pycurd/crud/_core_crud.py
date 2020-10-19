from abc import abstractmethod
from dataclasses import dataclass
from typing import Type, Iterable, List

from pycurd.crud.query_result_row import QueryResultRow
from pycurd.query import QueryInfo
from pycurd.types import RecordMapping, IDList
from pycurd.values import ValuesToWrite


@dataclass
class CoreCrud:
    @abstractmethod
    async def insert_many(self, table: Type[RecordMapping], values_list: Iterable[ValuesToWrite]) -> IDList:
        pass

    @abstractmethod
    async def update(self, info: QueryInfo, values: ValuesToWrite) -> IDList:
        pass

    @abstractmethod
    async def delete(self, info: QueryInfo) -> int:
        pass

    @abstractmethod
    async def get_list(self, info: QueryInfo) -> List[QueryResultRow]:
        pass

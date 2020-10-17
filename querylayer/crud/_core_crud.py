from abc import abstractmethod
from dataclasses import dataclass
from typing import Type, Iterable, List

from querylayer.crud.query_result_row import QueryResultRow
from querylayer.query import QueryInfo
from querylayer.types import RecordMapping, IDList
from querylayer.values import ValuesToWrite


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
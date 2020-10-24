import inspect
from dataclasses import dataclass
from typing import Any, Union, Dict, Type

import pypika
import tortoise
from tortoise.transactions import in_transaction

from pycurd.types import RecordMapping
from pycurd.crud.sql_crud import SQLCrud


@dataclass
class TortoiseCrud(SQLCrud):
    mapping2model: Dict[Type[RecordMapping], Union[str, Type[tortoise.models.Model]]]

    def __post_init__(self):
        for k, v in self.mapping2model.items():
            if inspect.isclass(v) and issubclass(v, tortoise.models.Model):
                self.mapping2model[k] = pypika.Table(v._meta.db_table)

        super().__post_init__()

    async def execute_sql(self, sql):
        try:
            async with in_transaction() as tconn:
                return await tconn.execute_query(sql)
        except Exception as e:
            print(e)
            await tconn.rollback()

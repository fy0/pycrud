import inspect
from dataclasses import dataclass
from typing import Any, Union, Dict, Type

import peewee
import pypika

from pycurd.types import RecordMapping
from pycurd.crud.sql_crud import SQLCrud


@dataclass
class PeeweeCrud(SQLCrud):
    mapping2model: Dict[Type[RecordMapping], Union[str, Type[peewee.Model]]]
    db: Any

    def __post_init__(self):
        for k, v in self.mapping2model.items():
            if inspect.isclass(v) and issubclass(v, peewee.Model):
                self.mapping2model[k] = pypika.Table(v._meta.table_name)

        super().__post_init__()

    async def execute_sql(self, sql):
        return self.db.execute_sql(sql)

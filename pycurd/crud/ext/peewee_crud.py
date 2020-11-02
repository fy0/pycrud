import inspect
from dataclasses import dataclass
from typing import Any, Union, Dict, Type

import pypika
import typing

from pycrud.types import RecordMapping
from pycrud.crud.sql_crud import SQLCrud, PlaceHolderGenerator

if typing.TYPE_CHECKING:
    import peewee


@dataclass
class PeeweeCrud(SQLCrud):
    mapping2model: Dict[Type[RecordMapping], Union[str, Type['peewee.Model']]]
    db: Any

    def __post_init__(self):
        import peewee
        for k, v in self.mapping2model.items():
            if inspect.isclass(v) and issubclass(v, peewee.Model):
                self.mapping2model[k] = pypika.Table(v._meta.table_name)

        super().__post_init__()

    def get_placeholder_generator(self) -> PlaceHolderGenerator:
        import peewee

        if isinstance(self.db, peewee.SqliteDatabase):
            return PlaceHolderGenerator('?')
        elif isinstance(self.db, peewee.PostgresqlDatabase):
            return PlaceHolderGenerator('${count}')
        elif isinstance(self.db, peewee.MySQLDatabase):
            return PlaceHolderGenerator('%s')
        else:
            raise Exception('unknown database: %s', self.db)

    async def execute_sql(self, sql, phg: PlaceHolderGenerator):
        return self.db.execute_sql(sql, phg.values)

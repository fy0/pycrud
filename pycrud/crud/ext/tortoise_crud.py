import inspect
from dataclasses import dataclass
from typing import Any, Union, Dict, Type

import pypika
import typing

from pycrud.types import RecordMapping
from pycrud.crud.sql_crud import SQLCrud, PlaceHolderGenerator, SQLExecuteResult
from pycrud.error import DBException

if typing.TYPE_CHECKING:
    import tortoise


@dataclass
class TortoiseCrud(SQLCrud):
    mapping2model: Dict[Type[RecordMapping], Union[str, Type['tortoise.models.Model']]]

    def __post_init__(self):
        import tortoise
        for k, v in self.mapping2model.items():
            if inspect.isclass(v) and issubclass(v, tortoise.models.Model):
                self.mapping2model[k] = pypika.Table(v._meta.db_table)

        self._phg_cache = None
        super().__post_init__()

    def get_placeholder_generator(self) -> PlaceHolderGenerator:
        if self._phg_cache is None:
            import tortoise
            SqliteClient, AsyncpgDBClient, MySQLClient = False, False, False

            try:
                from tortoise.backends.sqlite import SqliteClient
            except ImportError:
                pass

            try:
                from tortoise.backends.asyncpg import AsyncpgDBClient
            except ImportError:
                pass

            try:
                from tortoise.backends.mysql import MySQLClient
            except ImportError:
                pass

            conn = tortoise.transactions._get_connection(None)

            if SqliteClient and isinstance(conn, SqliteClient):
                self._phg_cache = '?'
            elif AsyncpgDBClient and isinstance(conn, AsyncpgDBClient):
                self._phg_cache = '${count}'
            elif MySQLClient and isinstance(conn, MySQLClient):
                self._phg_cache = '%s'
            else:
                raise Exception('unknown database: %s', conn)

        return PlaceHolderGenerator(self._phg_cache)

    async def execute_sql(self, sql: str, phg: PlaceHolderGenerator):
        from tortoise.transactions import in_transaction
        try:
            async with in_transaction() as tconn:
                if sql.startswith('INSERT INTO'):
                    r = await tconn.execute_insert(sql, phg.values)
                    return SQLExecuteResult(r)
                else:
                    r = await tconn.execute_query(sql, phg.values)
                    # rows affected, The resultset [1, {}]
                    print(r)
                    return r
        except Exception as e:
            await tconn.rollback()
            raise DBException(*e.args)

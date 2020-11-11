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
        from tortoise.fields import JSONField
        super().__post_init__()

        for k, v in self.mapping2model.items():
            if inspect.isclass(v) and issubclass(v, tortoise.models.Model):
                for name, f in v._meta.fields_map.items():
                    if f.SQL_TYPE.endswith('[]'):
                        self._table_cache[k]['array_fields'].add(name)
                    elif isinstance(f, JSONField):
                        self._table_cache[k]['json_fields'].add(name)

        for k, v in self.mapping2model.items():
            if inspect.isclass(v) and issubclass(v, tortoise.models.Model):
                self.mapping2model[k] = pypika.Table(v._meta.db_table)

        self._phg_cache = None
        self.is_pg = False

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
                self.is_pg = True
            elif MySQLClient and isinstance(conn, MySQLClient):
                self._phg_cache = '%s'
            else:
                raise Exception('unknown database: %s', conn)

        return PlaceHolderGenerator(self._phg_cache, self.json_dumps_func)

    async def execute_sql(self, sql: str, phg: PlaceHolderGenerator):
        from tortoise.transactions import in_transaction
        try:
            async with in_transaction() as tconn:
                if sql.startswith('INSERT INTO'):
                    if self.is_pg:
                        sql += ' RETURNING id'
                        r = await tconn.execute_insert(sql, phg.values)
                        # [<Record id=b'ff20'>]
                        return SQLExecuteResult(r[0])
                    else:
                        r = await tconn.execute_insert(sql, phg.values)
                        return SQLExecuteResult(r)
                else:
                    # rows affected, The resultset: [1, {}]
                    r = await tconn.execute_query(sql, phg.values)
                    r2 = [x.values() for x in r[1]]
                    return SQLExecuteResult(None, r2)
        except Exception as e:
            raise DBException(*e.args)

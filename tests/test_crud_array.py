from typing import Optional, List

import peewee
import pytest
from playhouse.postgres_ext import ArrayField
from pydantic import Field

from pycurd.crud.ext.peewee_crud import PeeweeCrud
from pycurd.crud.query_result_row import QueryResultRow
from pycurd.crud.sql_crud import PlaceHolderGenerator, SQLExecuteResult
from pycurd.query import QueryInfo
from pycurd.types import RecordMapping
from pycurd.values import ValuesToWrite

pytestmark = [pytest.mark.asyncio]


class TableOne(RecordMapping):
    id: Optional[int]
    arr: List[str] = Field(default_factory=lambda: [])


class SpecialCrud(PeeweeCrud):
    async def execute_sql(self, sql: str, phg: PlaceHolderGenerator):
        self.last_sql = sql
        return SQLExecuteResult(None, [])


def crud_db_init():
    from playhouse.db_url import connect

    # 创建数据库
    db = connect("sqlite:///:memory:")

    class TableOneModel(peewee.Model):
        arr = ArrayField(peewee.TextField)

        class Meta:
            database = db
            table_name = 'table_one'

    db.connect()
    # db.create_tables([TableOneModel], safe=True)

    c = SpecialCrud(None, {
        TableOne: TableOneModel,
    }, db)

    return c, db, TableOneModel


async def test_curd_array_extend():
    c, db, TableOneModel = crud_db_init()
    await c.update(QueryInfo.from_table_raw(TableOne), values=ValuesToWrite({
        'arr.array_extend': ['aa', 'bb']
    }, table=TableOne, try_parse=True))
    assert c.last_sql == 'UPDATE "table_one" SET "arr"="arr"||? WHERE "id" IN ()'


async def test_curd_array_extend_distinct():
    c, db, TableOneModel = crud_db_init()
    await c.update(QueryInfo.from_table_raw(TableOne), values=ValuesToWrite({
        'arr.array_extend_distinct': ['aa', 'bb']
    }, table=TableOne, try_parse=True))
    assert c.last_sql == 'UPDATE "table_one" SET "arr"=ARRAY(SELECT DISTINCT unnest("arr"||?)) WHERE "id" IN ()'


async def test_curd_array_prune_distinct():
    c, db, TableOneModel = crud_db_init()
    await c.update(QueryInfo.from_table_raw(TableOne), values=ValuesToWrite({
        'arr.array_prune_distinct': ['aa', 'bb']
    }, table=TableOne, try_parse=True))
    assert c.last_sql == 'UPDATE "table_one" SET "arr"=array(SELECT unnest("arr") EXCEPT SELECT unnest(?)) WHERE "id" IN ()'

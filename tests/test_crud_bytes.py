from typing import Optional

import peewee
import pytest

from pycurd.crud.ext.peewee_crud import PeeweeCrud
from pycurd.pydantic_ext.hex_string import HexString
from pycurd.query import QueryInfo, QueryConditions, ConditionExpr
from pycurd.types import RecordMapping

pytestmark = [pytest.mark.asyncio]


class ATest(RecordMapping):
    id: Optional[int]
    token: HexString


def crud_db_init():
    from playhouse.db_url import connect

    # 创建数据库
    # db = connect("sqlite:///database.db")
    db = connect("sqlite:///:memory:")

    class TestModel(peewee.Model):
        token = peewee.BlobField()

        class Meta:
            database = db
            table_name = 'users'

    db.connect()
    db.create_tables([TestModel], safe=True)

    TestModel.create(token=b'abcd')

    c = PeeweeCrud(None, {
        ATest: TestModel,
    }, db)

    return db, c, TestModel


async def test_bytes_read():
    db, c, TestModel = crud_db_init()

    info = QueryInfo(ATest)
    info.select = [ATest.token]
    info.conditions = QueryConditions([])

    ret = await c.get_list(info)
    assert ret[0].to_dict()['token'] == b'abcd'
    assert len(ret) == TestModel.select().count()


async def test_bytes_query():
    db, c, TestModel = crud_db_init()

    info = QueryInfo.from_json(ATest, {
        'token.eq': b'abcd'
    })

    ret = await c.get_list(info)
    assert ret[0].to_dict()['token'] == b'abcd'
    assert len(ret) == TestModel.select().count()


async def test_bytes_query_memoryview():
    db, c, TestModel = crud_db_init()

    info = QueryInfo.from_json(ATest, {
        'token.eq': memoryview(b'abcd')
    })

    ret = await c.get_list(info)
    assert ret[0].to_dict()['token'] == b'abcd'
    assert len(ret) == TestModel.select().count()


async def test_bytes_serializable():
    _, c, _ = crud_db_init()
    assert c.json_dumps_func(b'\x11\x22') == '"1122"'

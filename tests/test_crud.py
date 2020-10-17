from typing import Optional

import peewee
import pytest

from querylayer.const import QUERY_OP_COMPARE
from querylayer.crud.ext.peewee_crud import PeeweeCrud
from querylayer.crud.query_result_row import QueryResultRow
from querylayer.query import QueryInfo, QueryConditions, ConditionExpr
from querylayer.types import RecordMapping

pytestmark = [pytest.mark.asyncio]


class User(RecordMapping):
    id: int
    nickname: str
    username: str
    password: str
    test: int = 1


class Topic(RecordMapping):
    id: int
    title: str
    user_id: int
    hello: Optional[str] = None


def crud_db_init():
    from playhouse.db_url import connect

    # 创建数据库
    # db = connect("sqlite:///database.db")
    db = connect("sqlite:///:memory:")

    class Users(peewee.Model):
        name = peewee.CharField(index=True, max_length=255)
        username = peewee.TextField()
        nickname = peewee.TextField()
        password = peewee.TextField()

        class Meta:
            database = db
            table_name = 'user'

    class Topics(peewee.Model):
        title = peewee.CharField(index=True, max_length=255)
        time = peewee.BigIntegerField(index=True)
        content = peewee.TextField()
        user_id = peewee.IntegerField()

        class Meta:
            database = db
            table_name = 'topic'

    class Topics2(peewee.Model):
        title = peewee.CharField(index=True, max_length=255)
        time = peewee.BigIntegerField(index=True)
        content = peewee.TextField()
        user_id = peewee.IntegerField()

        class Meta:
            database = db

    db.connect()
    db.create_tables([Users, Topics, Topics2], safe=True)

    Users.create(name=1, username='test', nickname=2, password='pass')
    Users.create(name=11, username='test2', nickname=2, password='pass')
    Users.create(name=21, username='test3', nickname=2, password='pass')
    Users.create(name=31, username='test4', nickname=2, password='pass')
    Users.create(name=41, username='test5', nickname=2, password='pass')

    Topics.create(title='test', time=1, content='content1', user_id=1)
    Topics.create(title='test2', time=1, content='content2', user_id=1)
    Topics.create(title='test3', time=1, content='content3', user_id=2)
    Topics.create(title='test4', time=1, content='content4', user_id=2)

    Topics2.create(title='test', time=1, content='content1', user_id=1)
    Topics2.create(title='test2', time=1, content='content2', user_id=1)
    Topics2.create(title='test3', time=1, content='content3', user_id=2)
    Topics2.create(title='test4', time=1, content='content4', user_id=2)

    return db, Users, Topics, Topics2


async def test_curd_simple():
    db, MUsers, MTopics, MTopics2 = crud_db_init()

    info = QueryInfo(User)
    info.select = [User.id, User.username, User.password, User.nickname]
    info.conditions = QueryConditions([])

    c = PeeweeCrud(None, {
        User: 'users',
        Topic: 'topic',
    }, db)

    ret = await c.get_list(info)
    assert len(ret) == MUsers.select().count()

    for i in ret:
        assert isinstance(i, QueryResultRow)
        assert isinstance(i.id, int)

    info.conditions.items.append(ConditionExpr(User.id, QUERY_OP_COMPARE.EQ, 2))
    ret = await c.get_list(info)
    assert len(ret) == 1

    info.foreign_keys = {
        'topic': QueryInfo(Topic, [Topic.id, Topic.title], conditions=QueryConditions([
            ConditionExpr(Topic.user_id, QUERY_OP_COMPARE.EQ, 2),
        ]), foreign_keys={
            'user': QueryInfo(User, [User.id, User.nickname], conditions=QueryConditions([
                ConditionExpr(Topic.user_id, QUERY_OP_COMPARE.EQ, User.id),
            ]))
        }),
    }
    ret = await c.get_list_with_foreign_keys(info)
    print(222, ret)
    assert False


async def test_curd_write():
    # db, Users, Topics, Topics2 = crud_db_init()
    pass

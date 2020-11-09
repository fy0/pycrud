from typing import Optional

import peewee
import pytest

from pycurd.const import QUERY_OP_COMPARE, QUERY_OP_RELATION
from pycurd.crud.ext.peewee_crud import PeeweeCrud
from pycurd.crud.query_result_row import QueryResultRow
from pycurd.query import QueryInfo, QueryConditions, ConditionExpr
from pycurd.types import RecordMapping
from pycurd.values import ValuesToWrite

pytestmark = [pytest.mark.asyncio]


class User(RecordMapping):
    id: Optional[int]
    nickname: str
    username: str
    password: str = 'password'


class Topic(RecordMapping):
    id: Optional[int]
    title: str
    user_id: int
    content: Optional[str] = None
    time: int


def crud_db_init():
    from playhouse.db_url import connect

    # 创建数据库
    # db = connect("sqlite:///database.db")
    db = connect("sqlite:///:memory:")

    class Users(peewee.Model):
        username = peewee.TextField(index=True)
        nickname = peewee.TextField()
        password = peewee.TextField()

        class Meta:
            database = db
            table_name = 'users'

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

    Users.create(username='test', nickname=2, password='pass')
    Users.create(username='test2', nickname=2, password='pass')
    Users.create(username='test3', nickname=2, password='pass')
    Users.create(username='test4', nickname=2, password='pass')
    Users.create(username='test5', nickname=2, password='pass')

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
        'topic[]': QueryInfo(Topic, [Topic.id, Topic.title, Topic.user_id], conditions=QueryConditions([
            ConditionExpr(Topic.user_id, QUERY_OP_RELATION.IN, [2, 3]),
        ])),
        'topic': QueryInfo(Topic, [Topic.id, Topic.title, Topic.user_id], conditions=QueryConditions([
            ConditionExpr(Topic.user_id, QUERY_OP_RELATION.IN, [2, 3]),
        ]), foreign_keys={
            'user': QueryInfo(User, [User.id, User.nickname], conditions=QueryConditions([
                ConditionExpr(Topic.user_id, QUERY_OP_COMPARE.EQ, User.id),
            ]))
        }),
    }

    ret = await c.get_list_with_foreign_keys(info)
    assert ret[0].id == 2
    d = ret[0].to_dict()

    assert d['$extra']['topic']['id'] == 3
    assert d['$extra']['topic']['title'] == 'test3'
    assert d['$extra']['topic']['$extra']['user']
    assert d['$extra']['topic']['$extra']['user']['id'] == 2

    assert len(d['$extra']['topic[]']) == 2


async def test_curd_read_2():
    db, MUsers, MTopics, MTopics2 = crud_db_init()

    c = PeeweeCrud(None, {
        User: MUsers,
        Topic: MTopics,
    }, db)

    n0 = QueryInfo.from_json(Topic, {
        'id.eq': 1
    })
    n = n0.clone()

    ret = await c.get_list(n)
    assert len(ret) == 1


async def test_curd_read_by_prefix():
    db, MUsers, MTopics, MTopics2 = crud_db_init()

    c = PeeweeCrud(None, {
        User: MUsers
    }, db)

    n = QueryInfo.from_json(User, {
        'username.prefix': 'test4'
    })

    ret = await c.get_list(n)
    assert ret[0].to_dict()['username'] == 'test4'


async def test_curd_read_with_count():
    db, MUsers, MTopics, MTopics2 = crud_db_init()

    c = PeeweeCrud(None, {
        Topic: MTopics,
    }, db)

    i = QueryInfo.from_json(Topic, {})
    i.limit = 1
    ret = await c.get_list(i, with_count=True)
    assert len(ret) == 1
    assert ret.rows_count == MTopics.select().count()


async def test_curd_and_or():
    db, MUsers, MTopics, MTopics2 = crud_db_init()
    c = PeeweeCrud(None, {User: MUsers}, db)

    info = QueryInfo.from_json(User, {
        '$or': {
            'id.in': [1, 2],
            '$and': {
                'id.ge': 4,
                'id.le': 5
            }
        }
    })

    ret = await c.get_list(info)
    assert [x.id for x in ret] == [1, 2, 4, 5]


async def test_curd_write_success():
    db, MUsers, MTopics, MTopics2 = crud_db_init()

    c = PeeweeCrud(None, {
        User: MUsers,
        Topic: MTopics,
    }, db)

    v = ValuesToWrite({
        'user_id': '444',
        'content': 'welcome'
    }, Topic).bind()

    ret = await c.update(QueryInfo(Topic, []), v)
    assert ret == [1, 2, 3, 4]

    for i in MTopics.select():
        assert i.content == 'welcome'


async def test_curd_insert_success():
    db, MUsers, MTopics, MTopics2 = crud_db_init()

    c = PeeweeCrud(None, {
        User: MUsers,
        Topic: MTopics,
    }, db)

    v = ValuesToWrite({
        'title': 'test',
        'user_id': 1,
        'content': 'insert1',
        'time': 123
    }, Topic)
    v.bind(True)

    ret = await c.insert_many(Topic, [v])
    assert ret == [5]

    for i in MTopics.select().where(MTopics.id.in_(ret)):
        assert i.content == 'insert1'


async def test_curd_delete_success():
    db, MUsers, MTopics, MTopics2 = crud_db_init()

    c = PeeweeCrud(None, {
        User: MUsers,
        Topic: MTopics,
    }, db)

    assert MTopics.select().where(MTopics.id == 1).count() == 1

    ret = await c.delete(QueryInfo.from_json(Topic, {
        'id.eq': 1
    }))

    assert len(ret) == 1
    assert MTopics.select().where(MTopics.id == 1).count() == 0

import asyncio
import re
from dataclasses import dataclass

import peewee
from pypika import Table

from querylayer.const import QUERY_OP_COMPARE
from querylayer.crud import SQLCrud, PeeweeCrud
from querylayer.query import QueryInfo, QueryConditions, ConditionExpr
from querylayer.types import RecordMapping


@dataclass
class User(RecordMapping):
    id: int
    nickname: str
    username: str
    password: str
    test: int = 1


@dataclass
class Topic(RecordMapping):
    id: int
    title: str
    user_id: int


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


class Topics(peewee.Model):
    title = peewee.CharField(index=True, max_length=255)
    time = peewee.BigIntegerField(index=True)
    content = peewee.TextField()
    user_id = peewee.IntegerField()

    class Meta:
        database = db


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


async def main():
    '''
    f().or_(
        f(User.nickname).binary(QUERY_OP.EQ, 1),
        f(User.nickname).binary(QUERY_OP.EQ, 2),
    )'''

    q = QueryInfo(User)
    q.select = [
        User.id,
        User.username,
        User.password,
        User.nickname,
    ]

    q.conditions = QueryConditions([])

    q.foreign_keys = {
        'topic': QueryInfo(Topic, [Topic.id, Topic.title], conditions=QueryConditions([
            # ConditionExpr(Topic.id, QUERY_OP_COMPARE.EQ, User.id),
            ConditionExpr(Topic.user_id, QUERY_OP_COMPARE.EQ, 2),
            # ConditionLogicExpr('and', [
            #     ConditionExpr(Topic.id, QUERY_OP_COMPARE.EQ, '3')
            # ])
            # ConditionExpr(Topic.id, QUERY_OP_COMPARE.EQ, '3')
        ]), foreign_keys={
            'user': QueryInfo(User, [User.id, User.nickname], conditions=QueryConditions([
                ConditionExpr(Topic.user_id, QUERY_OP_COMPARE.EQ, User.id),
            ]))
        }),
        # 'topic[]': QueryInfo(Topic, [Topic.id, Topic.title], conditions=QueryConditions([
        #     ConditionExpr(Topic.id, QUERY_OP_COMPARE.EQ, User.id)
        # ]))
    }

    c = PeeweeCrud({
        User: Table('users'),
        Topic: Table('topics')
    }, db)
    # print('list', c.get_list(q))

    c.get_list()

    r = await c.get_list_with_foreign_keys(q)
    for i in r:
        a = User.from_data(i)
        print(222, a, i)
        print(i.to_dict())

    # print(q.to_json())
    print(type(Topic.id))
    print(Topic.__dataclass_fields__.keys())

    print(222, [getattr(Topic, x) for x in Topic.__dataclass_fields__.keys()])

    # print(type(Topic.__dataclass_fields__['id']))

    q = QueryInfo.parse_json(User, {
        '$select': 'id, nickname, username',
        '$select-': ''
    })
    print(q)

asyncio.run(main())

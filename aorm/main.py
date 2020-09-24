from dataclasses import dataclass
from functools import reduce

import peewee
from peewee import ModelSelect
from playhouse.shortcuts import model_to_dict

from aorm.const import QUERY_OP_COMPARE, QUERY_OP_RELATION
from aorm.query import QueryInfo, SelectExpr, QueryConditions, ConditionExpr, ConditionLogicExpr
from aorm.types import RecordMapping


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


from peewee import *
from playhouse.db_url import connect


# 创建数据库
# db = connect("sqlite:///database.db")
db = connect("sqlite:///:memory:")


class Users(Model):
    name = CharField(index=True, max_length=255)
    username = TextField()
    nickname = TextField()
    password = TextField()

    class Meta:
        database = db


class Topics(Model):
    title = CharField(index=True, max_length=255)
    time = BigIntegerField(index=True)
    content = TextField()
    user_id = IntegerField()

    class Meta:
        database = db


db.connect()
db.create_tables([Users, Topics], safe=True)

Users.create(name=1, username='test', nickname=2, password='pass')
Users.create(name=11, username='test2', nickname=2, password='pass')
Users.create(name=21, username='test3', nickname=2, password='pass')
Users.create(name=31, username='test4', nickname=2, password='pass')
Users.create(name=41, username='test5', nickname=2, password='pass')

Topics.create(title='test', time=1, content='content1', user_id=1)
Topics.create(title='test2', time=1, content='content2', user_id=1)
Topics.create(title='test3', time=1, content='content3', user_id=2)
Topics.create(title='test4', time=1, content='content4', user_id=2)


name2model = {
    'user': Users,
    'topic': Topics
}

_peewee_method_map = {
    # '+': '__pos__',
    # '-': '__neg__',
    QUERY_OP_COMPARE.EQ: '__eq__',
    QUERY_OP_COMPARE.NE: '__ne__',
    QUERY_OP_COMPARE.LT: '__lt__',
    QUERY_OP_COMPARE.LE: '__le__',
    QUERY_OP_COMPARE.GE: '__ge__',
    QUERY_OP_COMPARE.GT: '__gt__',
    QUERY_OP_RELATION.IN: '__lshift__',  # __lshift__ = _e(OP.IN)
    QUERY_OP_RELATION.NOT_IN: 'not_in',
    QUERY_OP_RELATION.IS: '__rshift__',  # __rshift__ = _e(OP.IS)
    QUERY_OP_RELATION.IS_NOT: '__rshift__',
    QUERY_OP_RELATION.CONTAINS: 'contains',
    QUERY_OP_RELATION.CONTAINS_ANY: 'contains_any',
    QUERY_OP_RELATION.PREFIX: 'startswith',
}


class PeeweeCrud:
    def get_list_with_foreign_keys(self, info: QueryInfo):
        ret = self.get_list(info)

        for i in ret:
            r = model_to_dict(i)
            print(r)

            if info.foreign_keys:
                for k, v in info.foreign_keys.items():
                    print(k)

    def get_list(self, info: QueryInfo, vars=None):
        select_fields = []
        model = name2model[info.from_table.name]

        # 选择项
        for i in info.select:
            select_fields.append(getattr(name2model[i.table.name], i))

        q = ModelSelect(model, select_fields)

        # 构造条件
        if info.conditions:
            def solve_condition(c):
                if isinstance(c, QueryConditions):
                    return [solve_condition(x) for x in c.items]

                elif isinstance(c, (QueryConditions, ConditionLogicExpr)):
                    items = [solve_condition(x) for x in c.items]
                    if items:
                        if c.type == 'and':
                            return reduce(peewee.Expression.__and__, items)
                        else:
                            return reduce(peewee.Expression.__or__, items)

                elif isinstance(c, ConditionExpr):
                    field = getattr(name2model[c.table_name], c.column)

                    cond = getattr(field, _peewee_method_map[c.op])(c.value)
                    if c.op == QUERY_OP_RELATION.IS_NOT:
                        cond = ~cond
                    return cond

            ret = solve_condition(info.conditions)
            if ret:
                q = q.where(*ret)

        # 一些限制
        q = q.limit(info.limit)
        q = q.offset(info.offset)

        # 查询结果
        return q


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

q.conditions = QueryConditions([
    ConditionLogicExpr(
        'or',
        [
            ConditionExpr(
                User.username,
                QUERY_OP_COMPARE.EQ,
                'test',
            ),
            ConditionExpr(
                User.id,
                QUERY_OP_COMPARE.EQ,
                '3',
            )
        ]
    ),
    ConditionExpr(
        User.username,
        QUERY_OP_COMPARE.EQ,
        'test',
    )
])


q.foreign_keys = {
    'topic': QueryInfo(Topic, [Topic.id, Topic.title], conditions=QueryConditions([
        ConditionExpr(Topic.id, QUERY_OP_COMPARE.EQ, User.id)
    ])),
    'topic[]': QueryInfo(Topic, [Topic.id, Topic.title], conditions=QueryConditions([
        ConditionExpr(Topic.id, QUERY_OP_COMPARE.EQ, User.id)
    ]))
}

c = PeeweeCrud()
print('list', c.get_list(q))


r = c.get_list_with_foreign_keys(q)
print(r)

# print(q.to_json())

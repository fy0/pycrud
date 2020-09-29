import re
from dataclasses import dataclass, field
from functools import reduce
from typing import Any, Union, Tuple, List, Dict, Type

import peewee
from pypika import Query, Table
from pypika.terms import ComplexCriterion

from aorm.const import QUERY_OP_COMPARE, QUERY_OP_RELATION
from aorm.query import QueryInfo, SelectExpr, QueryConditions, ConditionExpr, ConditionLogicExpr, QueryJoinInfo
from aorm.types import RecordMapping, RecordMappingField


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


name2model = {
    'user': Table('users'),
    'topic': Table('topics'),
    'topic2': Table('topics2')
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
    QUERY_OP_RELATION.IN: 'isin',  # __lshift__ = _e(OP.IN)
    QUERY_OP_RELATION.NOT_IN: 'notin',
    QUERY_OP_RELATION.IS: '__eq__',  # __rshift__ = _e(OP.IS)
    QUERY_OP_RELATION.IS_NOT: '__ne__',
    QUERY_OP_RELATION.CONTAINS: 'contains',
    QUERY_OP_RELATION.CONTAINS_ANY: 'contains_any',
    QUERY_OP_RELATION.PREFIX: 'startswith',
}


def get_class_full_name(cls):
    return '%s.%s' % (cls.__module__, cls.__qualname__)


def camel_case_to_underscore_case(raw_name):
    name = re.sub(r'([A-Z]{2,})', r'_\1', re.sub(r'([A-Z][a-z]+)', r'_\1', raw_name))
    if name.startswith('_'):
        name = name[1:]
    return name.lower()


@dataclass
class QueryResultRow:
    id: Any
    raw_data: Union[Tuple, List]
    info: QueryInfo

    base: Type[RecordMapping]
    extra: Any = field(default_factory=lambda: {})

    def to_dict(self):
        data = {}
        for i, j in zip(self.info.select_for_curd, self.raw_data):
            if i.table == self.base:
                data[i] = j

        if self.extra:
            ex = {}
            for k, v in self.extra.items():
                if isinstance(v, List):
                    ex[k] = [x.to_dict() for x in v]
                elif isinstance(v, QueryResultRow):
                    ex[k] = v.to_dict()
                else:
                    ex[k] = None
            data['$extra'] = ex
        return data

    def __repr__(self):
        return '<%s %s id: %s>' % (self.__class__.__name__, get_class_full_name(self.info.from_table), self.id)


class PeeweeCrud:
    def get_list_with_foreign_keys(self, info: QueryInfo):
        ret = self.get_list(info)
        pk_items = [x.id for x in ret]

        def solve(pk_items, main_table, fk_queries, up_results):
            for raw_name, query in fk_queries.items():
                query: QueryInfo
                limit = 0 if raw_name.endswith('[]') else 1

                # 上级ID，数据，查询条件
                q = QueryInfo(main_table, [query.from_table.id, *query.select])
                q.conditions = QueryConditions([ConditionExpr(info.from_table.id, QUERY_OP_RELATION.IN, pk_items)])
                q.join = [QueryJoinInfo(query.from_table, query.conditions, limit=limit)]

                elist = []
                for x in self.get_list(q):
                    x.base = query.from_table
                    elist.append(x)

                extra: Dict[Any, Union[List, QueryResultRow]] = {}

                if limit != 1:
                    for x in elist:
                        extra.setdefault(x.id, [])
                        extra[x.id].append(x)
                else:
                    for x in elist:
                        extra[x.id] = x

                for i in up_results:
                    i.extra[raw_name] = extra.get(i.id)

                if query.foreign_keys:
                    solve([x.id for x in elist], query.from_table, query.foreign_keys, elist)

        solve(pk_items, info.from_table, info.foreign_keys, ret)
        return ret

    def get_list(self, info: QueryInfo):
        model = name2model[info.from_table.name]

        # 选择项
        q = Query()
        q = q.from_(model)

        select_fields = [model.id]
        for i in info.select_for_curd:
            select_fields.append(getattr(name2model[i.table.name], i))

        q = q.select(*select_fields)

        # 构造条件
        if info.conditions:
            def solve_condition(c):
                if isinstance(c, QueryConditions):
                    items = list([solve_condition(x) for x in c.items])
                    if items:
                        return reduce(ComplexCriterion.__and__, items)  # 部分orm在实现join条件的时候拼接的语句不正确

                elif isinstance(c, (QueryConditions, ConditionLogicExpr)):
                    items = [solve_condition(x) for x in c.items]
                    if items:
                        if c.type == 'and':
                            return reduce(ComplexCriterion.__and__, items)
                        else:
                            return reduce(ComplexCriterion.__or__, items)

                elif isinstance(c, ConditionExpr):
                    field = getattr(name2model[c.table_name], c.column)

                    if isinstance(c.value, RecordMappingField):
                        real_value = getattr(name2model[c.value.table.name], c.value)
                    else:
                        real_value = c.value

                    cond = getattr(field, _peewee_method_map[c.op])(real_value)
                    return cond

            ret = solve_condition(info.conditions)
            if ret:
                q = q.where(ret)

            if info.join:
                for ji in info.join:
                    jtable = name2model[ji.table.name]
                    where = solve_condition(ji.conditions)

                    if ji.limit == 0:
                        q = q.inner_join(jtable).on(where)
                    else:
                        q = q.inner_join(jtable).on(
                            jtable.id == Query.from_(jtable).select(jtable.id).where(where).limit(ji.limit)
                        )

        # 一些限制
        q = q.limit(info.limit)
        q = q.offset(info.offset)

        # 查询结果
        ret = []
        cursor = db.execute_sql(q.get_sql())

        for i in cursor:
            ret.append(QueryResultRow(i[0], i[1:], info, info.from_table))

        return ret


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
    # ConditionLogicExpr(
    #     'or',
    #     [
    #         ConditionExpr(
    #             User.username,
    #             QUERY_OP_COMPARE.EQ,
    #             'test',
    #         ),
    #         ConditionExpr(
    #             User.id,
    #             QUERY_OP_COMPARE.EQ,
    #             '3',
    #         )
    #     ]
    # ),
    # ConditionExpr(
    #     User.username,
    #     QUERY_OP_COMPARE.EQ,
    #     'test',
    # )
])


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

c = PeeweeCrud()
# print('list', c.get_list(q))

r = c.get_list_with_foreign_keys(q)
for i in r:
    print(i.to_dict())


# print(q.to_json())

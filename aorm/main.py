from dataclasses import dataclass

from peewee import ModelSelect

from aorm.const import QUERY_OP_COMPARE
from aorm.query import QueryInfo, SelectExpr, QueryConditions, ConditionExpr
from aorm.types import RecordMapping


@dataclass
class User(RecordMapping):
    nickname: str
    username: str
    password: str
    test: int = 1


'''
f().or_(
    f(User.nickname).binary(QUERY_OP.EQ, 1),
    f(User.nickname).binary(QUERY_OP.EQ, 2),
)'''


q = QueryInfo(User)
q.select = [
    SelectExpr(User.username),
    SelectExpr(User.password),
    SelectExpr(User.nickname),
]

q.conditions = QueryConditions([
    ConditionExpr(
        User.username,
        QUERY_OP_COMPARE.EQ,
        'test',
    )
])

from peewee import *
from playhouse.db_url import connect


# 创建数据库
db = connect("sqlite:///database.db")


class Users(Model):
    name = CharField(index=True, max_length=255)
    username = TextField()
    nickname = TextField()
    password = TextField()

    class Meta:
        database = db


class Topic(Model):
    title = CharField(index=True, max_length=255)
    time = BigIntegerField(index=True)
    content = TextField()

    class Meta:
        database = db


db.connect()
db.create_tables([Users, Topic], safe=True)


name2model = {
    'user': Users,
    'topic': Topic
}


class PeeweeCrud:
    def get_list(self, info: QueryInfo):
        models = []
        select_fields = []

        for i in info.from_all_tables:
            models.append(name2model[i.table_name])

        for i in info.select:
            select_fields.append(getattr(name2model[i.column.table.table_name], i.column))

        q = ModelSelect(models[0], select_fields)
        for i in q:
            print(i)


c = PeeweeCrud()
c.get_list(q)

print(q)
print(q.to_json())

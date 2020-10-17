import asyncio
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any, Union, Literal, Set

import peewee
from multidict import istr

from querylayer.crud.ext.peewee_crud import PeeweeCrud
from querylayer.permission import A, PermissionDesc, RolePerm, TablePerm
from querylayer.query import QueryInfo
from querylayer.types import RecordMapping, RecordMappingField
from slim import Application
from slim.base._view.base_view import BaseView
from slim.base._view.request_view import RequestView
from slim.exception import InvalidParams

app = Application()


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


class User(RecordMapping):
    id: int
    nickname: str
    username: str
    password: str
    test: int = 1

    @classmethod
    async def before_query(cls, info: 'QueryInfo', user=None, *, req=None):
        print(111, info)


class Topic(RecordMapping):
    id: int
    title: str
    user_id: int
    hello: Optional[str] = None


permission = {
    'visitor': RolePerm({
        User: TablePerm({
            User.id: {A.WRITE},
        })
    }, match=None),

    'user': RolePerm({

    })
}


c = PeeweeCrud(permission, {
    User: 'users',
    Topic: 'topic',
}, db)


class DataView(BaseView):
    def bulk_num(self):
        bulk_key = istr('bulk')
        if bulk_key in self.headers:
            try:
                num = int(self.headers.get(bulk_key))
                if num <= 0:
                    # num invalid
                    return 1
                return num
            except ValueError:
                pass
            return -1
        return 1

    def _get_list_page_and_size(self, page, client_size) -> Tuple[int, int]:
        page = page.strip()

        if not page.isdigit():
            raise InvalidParams("`page` is not a number")
        page = int(page)

        if self.LIST_ACCEPT_SIZE_FROM_CLIENT and client_size:
            page_size_limit = self.LIST_PAGE_SIZE_CLIENT_LIMIT or self.LIST_PAGE_SIZE
            if client_size == '-1':  # -1 means all
                client_size = -1
            elif client_size.isdigit():  # size >= 0
                client_size = int(client_size)
                if client_size == 0:
                    # use default value
                    client_size = page_size_limit
                else:
                    if page_size_limit != -1:
                        client_size = min(client_size, page_size_limit)
            else:
                raise InvalidParams("`size` is not a number")
        else:
            client_size = self.LIST_PAGE_SIZE

        return page, client_size

    async def is_returning(self) -> bool:
        return istr('returning') in self.headers

    async def list(self):
        qi = QueryInfo.parse_json(User, self.params)
        lst = await c.get_list_with_foreign_keys(qi)
        return [x.to_dict() for x in lst]

    async def get(self):
        qi = QueryInfo.parse_json(User, self.params)
        qi.limit = 1
        lst = await c.get_list_with_foreign_keys(qi)
        if lst:
            return lst[0].to_dict()


@app.route.get('/list')
async def main(req: RequestView):
    qi = QueryInfo.parse_json(User, req.params)
    lst = await c.get_list_with_foreign_keys(qi)
    return [x.to_dict() for x in lst]


app.run('0.0.0.0', 3333)

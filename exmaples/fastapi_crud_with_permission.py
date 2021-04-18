import functools
from typing import Optional, List

import peewee
import uvicorn
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from playhouse.db_url import connect
from starlette.requests import Request

from pycrud.crud.base_crud import PermInfo
from pycrud.crud.ext.peewee_crud import PeeweeCrud
from pycrud.crud.query_result_row import QueryResultRow
from pycrud.helpers.fastapi_ext import QueryDto, PermissionDependsBuilder
from pycrud.permission import RoleDefine, TablePerm, A
from pycrud.query import QueryInfo
from pycrud.types import Entity
from pycrud.values import ValuesToUpdate


# ORM Initialize

db = connect("sqlite:///:memory:")


class UserModel(peewee.Model):
    nickname = peewee.TextField()
    username = peewee.TextField()
    password = peewee.TextField(default='password')  # just for example
    update_test = peewee.TextField(default='update')

    class Meta:
        table_name = 'users'
        database = db


db.create_tables([UserModel])
UserModel(nickname='a', username='a1').save()
UserModel(nickname='b', username='b2').save()
UserModel(nickname='c', username='c3').save()


# Crud Initialize


class User(Entity):
    id: Optional[int]
    nickname: str
    username: str
    password: str = 'password'
    update_test: str


c = PeeweeCrud({
    # visitor
    None: RoleDefine({
        User: TablePerm({
            User.id: {A.READ, A.QUERY},
            User.nickname: {A.READ},
            User.update_test: {A.READ, A.UPDATE}
        })
    }),
}, {
    User: 'users'
}, db)


# Web Service

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PDB(PermissionDependsBuilder):
    @classmethod
    def validate_role(cls, current_request_role: str):
        if current_request_role in ('user', None):
            return current_request_role

    @classmethod
    def get_user(cls, request: Request):
        pass


@app.post("/user/create")
async def user_create(item: User.dto.get_create(), perm=Depends(PDB.get_perm_info)):
    return await c.insert_many_with_perm(User, [item], perm=perm)  # response id list: [1]


@app.get("/user/list")
async def user_list(query_json=QueryDto(User, PDB), perm: PermInfo=Depends(PDB.get_perm_info)):
    q = QueryInfo.from_json(User, query_json)

    def solve(x: QueryResultRow):
        val = x.to_dict()
        return dict(User.dto.get_read(perm.role).parse_obj(val))

    return [solve(x) for x in await c.get_list(q)]


@app.post("/user/update")
async def user_update(item: User.dto.get_update(), query_json=QueryDto(User, PDB), perm=Depends(PDB.get_perm_info)):
    q = QueryInfo.from_json(User, query_json)
    return await c.update_with_perm(q, ValuesToUpdate(item), perm=perm)  # response id list: [1]


@app.post("/user/delete")
async def user_delete(query_json=QueryDto(User, PDB), perm=Depends(PDB.get_perm_info)):
    q = QueryInfo.from_json(User, query_json)
    return await c.delete_with_perm(q, perm=perm)  # response id list: [1]


print('Service Running ...')
uvicorn.run(app, host='0.0.0.0', port=3000)

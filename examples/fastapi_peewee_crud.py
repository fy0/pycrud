from typing import Optional

import peewee
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from playhouse.db_url import connect
from pycrud import Entity, ValuesToUpdate, ValuesToCreate
from pycrud.crud.ext.peewee_crud import PeeweeCrud
from pycrud.helpers.fastapi_ext import PermissionDependsBuilder
from pycrud.permission import RoleDefine
from pycrud.utils import UserObject


# ORM Initialize

db = connect('sqlite:///:memory:')


class UserModel(peewee.Model):
    nickname = peewee.TextField()
    username = peewee.TextField()
    password = peewee.TextField(default='password')  # just for example

    class Meta:
        table_name = 'users'
        database = db


db.create_tables([UserModel])


# Crud Initialize

class User(Entity):
    id: Optional[int]
    nickname: str
    username: str
    password: str = 'password'


c = PeeweeCrud(None, {
    User: 'users'
}, db)


class PDB(PermissionDependsBuilder):
    @classmethod
    async def validate_role(cls, user: UserObject, current_request_role: str) -> RoleDefine:
        return c.default_role

    @classmethod
    async def get_user(cls, request: Request) -> UserObject:
        pass


# Web Service

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/user/create", response_model=User.dto.resp_create())
async def user_create(item: User.dto.get_create()):
    return await c.insert_many(User, [ValuesToCreate(item)])  # response id list: [1]


@app.get("/user/list", response_model=User.dto.resp_list())
async def user_list(query=PDB.query_info_depends(User)):
    return [x.to_dict() for x in await c.get_list(query)]


@app.post("/user/update", response_model=User.dto.resp_update())
async def user_list(item: User.dto.get_update(), query=PDB.query_info_depends(User)):
    return await c.update(query, ValuesToUpdate(item))


@app.post("/user/delete", response_model=User.dto.resp_delete())
async def user_delete(query=PDB.query_info_depends(User)):
    return await c.delete(query)


print('Service Running ...')
uvicorn.run(app, host='0.0.0.0', port=3000)

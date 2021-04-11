from typing import Optional

import peewee
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from playhouse.db_url import connect
from pycrud.crud.ext.peewee_crud import PeeweeCrud
from pycrud.query import QueryInfo
from pycrud.types import Entity
from pycrud.values import ValuesToUpdate


# ORM Initialize

db = connect("sqlite:///:memory:")


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


# Web Service

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/user/create")
async def user_create(item: User):
    return await c.insert_many(User, [item])  # response id list: [1]


@app.get("/user/list")
async def user_list(request: Request):
    q = QueryInfo.from_json(User, request.query_params, True)
    return [x.to_dict() for x in await c.get_list(q)]


@app.post("/user/update")
async def user_list(request: Request, item: User.partial_model):
    q = QueryInfo.from_json(User, request.query_params, True)
    return await c.update(q, ValuesToUpdate(item))


@app.post("/user/delete")
async def user_delete(request: Request):
    q = QueryInfo.from_json(User, request.query_params, True)
    return await c.delete(q)  # response id list: [1]


print('Service Running ...')
uvicorn.run(app, host='0.0.0.0', port=3000)

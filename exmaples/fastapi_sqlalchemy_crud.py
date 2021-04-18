from typing import Optional

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String, Sequence

from pycrud.crud.ext.sqlalchemy_crud import SQLAlchemyCrud
from pycrud.helpers.fastapi_ext import QueryDto
from pycrud.query import QueryInfo
from pycrud.types import Entity
from pycrud.values import ValuesToUpdate


# ORM Initialize

engine = create_engine("sqlite:///:memory:")
Base = declarative_base()
Session = sessionmaker(bind=engine)


class UserModel(Base):
    __tablename__ = 'users'
    id = Column(Integer, Sequence('user_id_seq'), primary_key=True)
    nickname = Column(String)
    username = Column(String)
    password = Column(String, default='password')
    update_test: Column(String, default='update')


Base.metadata.create_all(engine)

session = Session()
session.add_all([
    UserModel(nickname='a', username='a1'),
    UserModel(nickname='b', username='b2'),
    UserModel(nickname='c', username='c3')
])
session.commit()


# Crud Initialize

class User(Entity):
    id: Optional[int]
    nickname: str
    username: str
    password: str = 'password'


c = SQLAlchemyCrud(None, {
    User: 'users'
}, engine)


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
async def user_create(item: User.dto.get_create()):
    return await c.insert_many(User, [item])  # response id list: [1]


@app.get("/user/list")
async def user_list(query_json=QueryDto(User)):
    q = QueryInfo.from_json(User, query_json)
    return [x.to_dict() for x in await c.get_list(q)]


@app.post("/user/update")
async def user_list(item: User.dto.get_update(), query_json=QueryDto(User)):
    q = QueryInfo.from_json(User, query_json)
    return await c.update(q, ValuesToUpdate(item))


@app.post("/user/delete")
async def user_delete(query_json=QueryDto(User)):
    q = QueryInfo.from_json(User, query_json)
    return await c.delete(q)  # response id list: [1]


print('Service Running ...')
uvicorn.run(app, host='0.0.0.0', port=3000)

from typing import Optional

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String, Sequence

from pycrud import Entity, ValuesToUpdate, ValuesToCreate, UserObject
from pycrud.crud.ext.sqlalchemy_crud import SQLAlchemyCrud
from pycrud.helpers.fastapi_ext import PermissionDependsBuilder
from pycrud.permission import RoleDefine


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


class PDB(PermissionDependsBuilder):
    @classmethod
    async def validate_role(cls, user: UserObject, current_request_role: str) -> RoleDefine:
        return c.default_role

    @classmethod
    async def get_user(cls, request: Request) -> UserObject:
        pass


# Web Service

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


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

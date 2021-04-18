from typing import Optional, List

import uvicorn
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String, Sequence

from pycrud.crud.base_crud import PermInfo
from pycrud.crud.ext.sqlalchemy_crud import SQLAlchemyCrud
from pycrud.crud.query_result_row import QueryResultRow
from pycrud.helpers.fastapi_ext import QueryDto, PermissionDependsBuilder
from pycrud.permission import RoleDefine, TablePerm, A
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
    update_test: str


c = SQLAlchemyCrud({
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

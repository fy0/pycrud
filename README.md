# pycrud

[![codecov](https://codecov.io/gh/fy0/pycrud/branch/master/graph/badge.svg)](https://codecov.io/gh/fy0/pycrud)

An async crud framework for RESTful API.

Features:

* Do CRUD operations by json.

* Easy to integrate with web framework.

* Works with popular orm.

* Role based permission system

* Data validate with pydantic.

* Tested coveraged

### Install:

```bash
pip install pycrud==1.0.0a0
```

### Examples:

#### CRUD service by fastapi and SQLAlchemy

```python
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

```

#### CRUD service with permission

See [Examples](/examples)

#### Query filter

```python
from pycrud.values import ValuesToUpdate
from pycrud.query import QueryInfo


async def fetch_list():
    # dsl version
    q1 = QueryInfo.from_table(User, where=[
        User.id == 1
    ])

    # json verison
    q2 = QueryInfo.from_json(User, {
        'id.eq': 1
    })

    lst = await c.get_list(q1)
    print([x.to_dict() for x in lst])


async def update_by_ids():
    v = ValuesToUpdate({'nickname': 'bbb', 'username': 'u2'})

    # from dsl
    q1 = QueryInfo.from_table(User, where=[
        User.id.in_([1, 2, 3])
    ])

    q2 = QueryInfo.from_json(User, {
        'id.in': [1,2,3]
    })

    lst = await c.update(q1, v)
    print(lst)


async def complex_filter_dsl():
    # $or: (id < 3) or (id > 5)
    (User.id < 3) | (User.id > 5)

    # $and: 3 < id < 5
    (User.id > 3) & (User.id < 5)

    # $not: not (3 < id < 5)
    ~((User.id > 3) & (User.id < 5))
    
    # logical condition: (id == 3) or (id == 4) or (id == 5)
    (User.id != 3) | (User.id != 4) | (User.id != 5)

    # logical condition: (3 < id < 5) or (10 < id < 15)
    ((User.id > 3) & (User.id < 5)) | ((User.id > 10) & (User.id < 15))


async def complex_filter_json():
    # $or: (id < 3) or (id > 5)
    QueryInfo.from_json(User, {
        '$or': {
            'id.lt': 3,  
            'id.gt': 5 
        }
    })
    
    # $and: 3 < id < 5
    QueryInfo.from_json(User, {
        '$and': {
            'id.gt': 3,  
            'id.lt': 5 
        }
    })
    
    # $not: not (3 < id < 5)
    QueryInfo.from_json(User, {
        '$not': {
            'id.gt': 3,  
            'id.lt': 5 
        }
    })

    # logical condition: (id == 3) or (id == 4) or (id == 5)
    QueryInfo.from_json(User, {
        '$or': {
            'id.eq': 3,  
            'id.eq.2': 4,
            'id.eq.3': 5, 
        }
    })

    # logical condition: (3 < id < 5) or (10 < id < 15)
    QueryInfo.from_json(User, {
        '$or': {
            '$and': {
                'id.gt': 3,
                'id.lt': 5
            },
            '$and.2': {
                'id.gt': 10,
                'id.lt': 15
            }
        }
    })
```

### Operators

| type | operator | text |
| ---- | -------- | ---- |
| compare | EQ | ('eq', '==') |
| compare | NE | ('ne', '!=') |
| compare | LT | ('lt', '<') |
| compare | LE | ('le', '<=') |
| compare | GE | ('ge', '>=') |
| compare | GT | ('gt', '>') |
| relation | IN | ('in',) |
| relation | NOT_IN | ('notin', 'not in') |
| relation | IS | ('is',) |
| relation | IS_NOT | ('isnot', 'is not') |
| relation | PREFIX | ('prefix',) |
| relation | CONTAINS | ('contains',) |
| logic | AND | ('and',) |
| logic | OR | ('or',) |

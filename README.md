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


### Examples:

#### CRUD service by peewee and fastapi

```python
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

```

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
    v = ValuesToWrite({'nickname': 'bbb', 'username': 'u2'})

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

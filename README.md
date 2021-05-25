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
pip install pycrud==1.0.0a1
```

### Examples:

#### CRUD service by fastapi and SQLAlchemy

```python
import uvicorn
from typing import Optional
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from model_sqlalchemy import engine, UserModel, TopicModel
from pycrud import Entity, ValuesToUpdate, ValuesToCreate, UserObject
from pycrud.crud.ext.sqlalchemy_crud import SQLAlchemyCrud
from pycrud.helpers.fastapi_ext import PermissionDependsBuilder

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
```

See docs at `http://localhost:3000/redoc`

You can make requests like:

`http://localhost:3000/topic/list?id.eq=1
http://localhost:3000/topic/list?id.gt=1
http://localhost:3000/topic/list?id.in=[2,3]
http://localhost:3000/topic/list?user_id.eq=1
`


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
| relation | CONTAINS_ALL | ('contains_all',) |
| relation | CONTAINS_ANY | ('contains_any',) |
| logic | AND | ('and',) |
| logic | OR | ('or',) |

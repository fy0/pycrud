# pycrud

[![codecov](https://codecov.io/gh/fy0/pycrud/branch/master/graph/badge.svg)](https://codecov.io/gh/fy0/pycrud)

A common crud framework for web.

Features:

* Generate query by json or dsl

* Role based permission system

* Easy to integrate with web framework

* Tested


### Examples:

#### Define

```python
from typing import Optional

from playhouse.db_url import connect
from pycrud.crud.ext.peewee_crud import PeeweeCrud
from pycrud.types import RecordMapping

class User(RecordMapping):
    id: Optional[int]
    nickname: str
    username: str
    password: str = 'password'


db = connect("sqlite:///:memory:")

c = PeeweeCrud(None, {
    User: 'users'
}, db)

```

#### Create

```python
from pycrud.values import ValuesToWrite

v = ValuesToWrite({'nickname': 'wwww', 'username': 'u2'})
lst = await c.insert_many(User, [v])

print(lst)
```

#### Read

```python
from pycrud.query import QueryInfo

# from dsl
lst = await c.get_list(QueryInfo.from_table_raw(User, where=[
    User.id != 1
]))

# from json
lst = await c.get_list(QueryInfo.from_json(User, {
    'id.eq': 1
}))

print([x.to_dict() for x in lst])
```

#### Update

```python
from pycrud.query import QueryInfo
from pycrud.values import ValuesToWrite

v = ValuesToWrite({'nickname': 'bbb', 'username': 'u2'})

# from dsl
lst = await c.update(QueryInfo.from_table_raw(User, where=[
    User.id.in_([1, 2, 3])
]))

# from json
lst = await c.update(QueryInfo.from_json(User, {
    'id.in': [1,2,3]
}), v)

print(lst)
```

#### Delete

```python
from pycrud.query import QueryInfo

lst = await c.delete(QueryInfo.from_json(User, {
    'id.in': [1,2,3]
}))

print(lst)
```

### Query by json

```python
from pycrud.query import QueryInfo

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

# multiple same operator: (id == 3) or (id == 4) or (id == 5)
QueryInfo.from_json(User, {
    '$or': {
        'id.eq': 3,  
        'id.eq.2': 4,
        'id.eq.3': 5, 
    }
})

# multiple same operator: (3 < id < 5) or (10 < id < 15)
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


### Query by DSL
```python
# $or: (id < 3) or (id > 5)
(User.id < 3) | (User.id > 5)

# $and: 3 < id < 5
(User.id > 3) & (User.id < 5)

# $not: not (3 < id < 5)
~((User.id > 3) & (User.id < 5))

# multiple same operator: (id == 3) or (id == 4) or (id == 5)
(User.id != 3) | (User.id != 4) | (User.id != 5)

# multiple same operator: (3 < id < 5) or (10 < id < 15)
((User.id > 3) & (User.id < 5)) | ((User.id > 10) & (User.id < 15))
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
| relation | NOT_IN | ('notin', 'not_in') |
| relation | IS | ('is',) |
| relation | IS_NOT | ('isnot', 'is_not') |
| relation | PREFIX | ('prefix',) |
| relation | CONTAINS | ('contains',) |
| relation | CONTAINS_ANY | ('contains_any',) |
| logic | AND | ('and',) |
| logic | OR | ('or',) |


```json5
// usage:
{
  'time.ge': 1,
  '$or': {
    'id.in': [1, 2, 3],
    '$and': {
      'time.ge': 100,
      'time.le': 500,
    }
  }
}
```

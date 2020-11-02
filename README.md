# pycrud

[![codecov](https://codecov.io/gh/fy0/querylayer/branch/master/graph/badge.svg)](https://codecov.io/gh/fy0/querylayer)

A common crud framework for web.

Features:

* Generate query by json

* Role based permission system

* Easy to bind

* Tested


### Examples:

#### Define

```python
from typing import Optional

from playhouse.db_url import connect
from pycurd.crud.ext.peewee_crud import PeeweeCrud
from pycurd.types import RecordMapping

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
from pycurd.values import ValuesToWrite

v = ValuesToWrite({'nickname': 'wwww', 'username': 'u2'})
lst = await c.insert_many(User, [v])

print(lst)
```

#### Read

```python
from pycurd.query import QueryInfo

lst = await c.get_list(QueryInfo.from_json(User, {
    'id.eq': 1
}))

print([x.to_dict() for x in lst])
```

#### Update

```python
from pycurd.query import QueryInfo
from pycurd.values import ValuesToWrite

v = ValuesToWrite({'nickname': 'bbb', 'username': 'u2'})
lst = await c.update(QueryInfo.from_json(User, {
    'id.in': [1,2,3]
}), v)

print(lst)
```

#### Delete

```python
from pycurd.query import QueryInfo

lst = await c.delete(QueryInfo.from_json(User, {
    'id.in': [1,2,3]
}))

print(lst)
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

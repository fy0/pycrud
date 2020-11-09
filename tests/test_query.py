from typing import Any, Union

from pycurd.query import QueryInfo
from pycurd.types import RecordMapping, RecordMappingField


class User(RecordMapping):
    id: int
    nickname: str
    username: str
    password: str


def test_query_select_exclude():
    q = QueryInfo.from_table_raw(User, select=[User.id, User.nickname, User.password], select_exclude=[User.nickname])
    assert q.select_for_curd == [User.id, User.password]

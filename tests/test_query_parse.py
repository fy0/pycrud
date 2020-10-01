import pytest
from dataclasses import dataclass

from datalayer.const import QUERY_OP_COMPARE
from datalayer.query import QueryInfo
from datalayer.types import RecordMapping


@dataclass
class User(RecordMapping):
    id: int
    nickname: str
    username: str
    password: str
    test: int = 1


def test_select_simple():
    q = QueryInfo.parse_json(User, {
        '$select': 'id, nickname, password',
        '$select-': ''
    })
    assert q.select_for_curd == [User.id, User.nickname, User.password]


def test_select_simple2():
    q = QueryInfo.parse_json(User, {})
    assert q.select_for_curd == [User.id, User.nickname, User.username, User.password, User.test]


def test_condition_simple():
    q = QueryInfo.parse_json(User, {
        'nickname.eq': 'test'
    })
    cond = q.conditions.items[0]
    assert cond.column == User.nickname
    assert cond.op == QUERY_OP_COMPARE.EQ
    assert cond.value == 'test'

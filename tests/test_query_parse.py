import re
import pytest
from dataclasses import dataclass

from querylayer.const import QUERY_OP_COMPARE
from querylayer.query import QueryInfo, ConditionLogicExpr
from querylayer.types import RecordMapping


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


def test_condition_simple2():
    q = QueryInfo.parse_json(User, {
        'nickname.eq': 'test',
        'test.lt': 5
    })
    cond = q.conditions.items[0]
    assert cond.column == User.nickname
    assert cond.op == QUERY_OP_COMPARE.EQ
    assert cond.value == 'test'
    cond = q.conditions.items[1]
    assert cond.column == User.test
    assert cond.op == QUERY_OP_COMPARE.LT
    assert cond.value == 5


@pytest.mark.parametrize('key, op_name', [('and', 'and'), ('or', 'or'), ('and1', 'and'), ('or0', 'or'), ('or10001', 'or')])
def test_condition_logic_1(key, op_name):
    q = QueryInfo.parse_json(User, {
        '$' + key: {
            'nickname.eq': 'test',
            'test.lt': 5
        }
    })
    cond = q.conditions.items[0]
    assert isinstance(cond, ConditionLogicExpr)
    assert cond.type == op_name
    cond1 = cond.items[0]
    cond2 = cond.items[1]
    assert cond1.op == QUERY_OP_COMPARE.EQ
    assert cond2.op == QUERY_OP_COMPARE.LT


def test_condition_logic_2():
    q = QueryInfo.parse_json(User, {
        '$and': {
            'nickname.eq': 'test',
            '$or': {
                'test.ge': 5,
                'test.lt': 10
            }
        }
    })

    cond = q.conditions.items[0]
    assert isinstance(cond, ConditionLogicExpr)
    assert cond.type == 'and'
    assert cond.items[0].op == QUERY_OP_COMPARE.EQ
    assert isinstance(cond.items[1], ConditionLogicExpr)
    assert cond.items[1].type == 'or'
    assert cond.items[1].items[1].value == 10


@pytest.mark.parametrize('key', ['$oracle', '$Or', '$OR'])
def test_condition_logic_failed_1(key):
    q = QueryInfo.parse_json(User, {
        '$' + key: {
            'nickname.eq': 'test',
            'test.lt': 5
        }
    })
    assert len(q.conditions.items) == 0

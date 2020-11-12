from typing import Any, Union

from pycrud.const import QUERY_OP_COMPARE
from pycrud.query import QueryInfo, ConditionLogicExpr, QueryConditions
from pycrud.types import RecordMapping, RecordMappingField


class User(RecordMapping):
    id: int
    nickname: str
    username: str
    password: str
    test: int = 1


def f(val) -> Union[RecordMappingField, Any]:
    return val


def test_select_dsl_simple():
    q = QueryInfo.from_table_raw(User, select=[User.id, User.nickname, User.password])
    assert q.select_for_crud == [User.id, User.nickname, User.password]


def test_select_simple2():
    q = QueryInfo.from_table_raw(User)
    assert q.select_for_crud == [User.id, User.nickname, User.username, User.password, User.test]


def test_dsl_condition_simple():
    q = QueryInfo.from_table_raw(User, where=[
        User.nickname == 'test'
    ])

    cond = q.conditions.items[0]
    assert cond.column == User.nickname
    assert cond.op == QUERY_OP_COMPARE.EQ
    assert cond.value == 'test'


def test_condition_simple2():
    q = QueryInfo.from_table_raw(User, where=[
        User.nickname == 'test',
        User.test < 5
    ])

    cond = q.conditions.items[0]
    assert cond.column == User.nickname
    assert cond.op == QUERY_OP_COMPARE.EQ
    assert cond.value == 'test'
    cond = q.conditions.items[1]
    assert cond.column == User.test
    assert cond.op == QUERY_OP_COMPARE.LT
    assert cond.value == 5


def test_condition_logic_2():
    q = QueryInfo.from_table_raw(User, where=[
        (User.nickname == 'test') & (
            (User.test >= 5) | (User.test <= 10)
        )
    ])

    cond = q.conditions.items[0]
    assert isinstance(cond, ConditionLogicExpr)
    assert cond.type == 'and'
    assert cond.items[0].op == QUERY_OP_COMPARE.EQ
    assert isinstance(cond.items[1], ConditionLogicExpr)
    assert cond.items[1].type == 'or'
    assert cond.items[1].items[1].value == 10

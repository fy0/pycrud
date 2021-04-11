import pytest

from pycrud.const import QUERY_OP_COMPARE
from pycrud.error import InvalidQueryConditionValue, InvalidQueryConditionOperator
from pycrud.query import QueryInfo, ConditionLogicExpr, QueryOrder, check_same_expr, QueryConditions
from pycrud.types import Entity, EntityField
from tests.test_query_dsl import f


class User(Entity):
    id: int
    nickname: str
    username: str
    password: str
    test: int = 1


class Topic(Entity):
    id: int
    title: str
    user_id: int


def test_select_simple():
    q = QueryInfo.from_json(User, {
        '$select': 'id, nickname, password',
        '$select-': ''
    })
    assert q.select_for_crud == [User.id, User.nickname, User.password]


def test_select_simple2():
    q = QueryInfo.from_json(User, {})
    assert q.select_for_crud == [User.id, User.nickname, User.username, User.password, User.test]


def test_condition_simple():
    q = QueryInfo.from_json(User, {
        'nickname.eq': 'test'
    })
    cond = q.conditions.items[0]
    assert cond.column == User.nickname
    assert cond.op == QUERY_OP_COMPARE.EQ
    assert cond.value == 'test'


def test_condition_simple2():
    q = QueryInfo.from_json(User, {
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
    q = QueryInfo.from_json(User, {
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
    q = QueryInfo.from_json(User, {
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
    q = QueryInfo.from_json(User, {
        '$' + key: {
            'nickname.eq': 'test',
            'test.lt': 5
        }
    })
    assert len(q.conditions.items) == 0


def test_condition_simple_from_http():
    q = QueryInfo.from_json(User, {
        'nickname.eq': '"test"'
    }, from_http_query=True)
    cond = q.conditions.items[0]
    assert cond.column == User.nickname
    assert cond.op == QUERY_OP_COMPARE.EQ
    assert cond.value == 'test'


def test_condition_simple2_from_http():
    q = QueryInfo.from_json(User, {
        'test.eq': '"111"'
    }, from_http_query=True)
    cond = q.conditions.items[0]
    assert cond.column == User.test
    assert cond.op == QUERY_OP_COMPARE.EQ
    assert cond.value == 111

    q = QueryInfo.from_json(User, {
        'test.eq': '222'
    }, from_http_query=True)
    cond = q.conditions.items[0]
    assert cond.column == User.test
    assert cond.op == QUERY_OP_COMPARE.EQ
    assert cond.value == 222


def test_parse_order_by():
    q = QueryInfo.from_json(User, {
        '$order-by': 'id, username.desc, test'
    })
    assert q.order_by == [QueryOrder(User.id), QueryOrder(User.username, 'desc'), QueryOrder(User.test)]


def test_parse_foreignkey_column_not_exists():
    with pytest.raises(InvalidQueryConditionValue) as e:
        QueryInfo.from_json(User, {
            '$fks': {'topic': {'id.eq': '$user:xxxx'}}
        })
        assert '$user:xxxx' in e.value


def f(val) -> EntityField:
    return val


def test_parse_multi_same_op():
    q = QueryInfo.from_json(User, {
        'id.ne': 1,
        'id.ne.1': 2,
        'id.ne.2': 3,
    })
    conds1 = q.conditions
    conds2 = QueryConditions([
        f(User.id) != 1,
        f(User.id) != 2,
        f(User.id) != 3,
    ])

    assert check_same_expr(conds1, conds2)


def test_parse_multi_same_op_failed():
    with pytest.raises(InvalidQueryConditionOperator):
        QueryInfo.from_json(User, {
            'id.ne.a': 1,
        })


def test_parse_negated():
    q = QueryInfo.from_json(User, {
        '$not': {
            'id.eq': 1,
        }
    })
    conds1 = q.conditions
    conds2 = QueryConditions([
        ~(ConditionLogicExpr('and', [f(User.id) == 1]))
    ])

    assert check_same_expr(conds1, conds2)


def test_parse_foreignkey():
    with pytest.raises(InvalidQueryConditionValue):
        QueryInfo.from_json(User, {
            '$fks': {'topic': {'id.eq': '$user.id'}}
        })

    q = QueryInfo.from_json(User, {
        '$fks': {'topic': {
            '$select': 'id, title, user_id',
            'user_id.eq': '$user:id'
        }}
    })

    assert 'topic' in q.foreign_keys

    t = q.foreign_keys['topic']
    assert t.entity == Topic
    assert t.select == [Topic.id, Topic.title, Topic.user_id]
    assert len(t.conditions.items) == 1

    c = t.conditions.items[0]
    assert c.column == Topic.user_id
    assert c.op == QUERY_OP_COMPARE.EQ
    assert c.value == User.id

from pycrud.pydantic_ext.hex_string import HexString
from pycrud.query import QueryInfo, ConditionLogicExpr
from pycrud.types import Entity


class User(Entity):
    id: int
    nickname: str
    token: HexString


def test_hexstr_simple():
    q = QueryInfo.from_json(User, {
        '$select': 'id, nickname, token',
        'token.eq': 'aa11'
    })
    assert q.conditions.items[0].value == b'\xaa\x11'

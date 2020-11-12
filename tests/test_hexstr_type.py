import json

from pycrud.pydantic_ext.hex_string import HexString
from pycrud.query import QueryInfo, ConditionLogicExpr
from pycrud.types import RecordMapping


class User(RecordMapping):
    id: int
    nickname: str
    token: HexString


def test_hexstr_simple():
    q = QueryInfo.from_json(User, {
        '$select': 'id, nickname, token',
        'token.eq': 'aa11'
    })
    assert q.conditions.items[0].value == b'\xaa\x11'


def test_hexstr_in():
    q = QueryInfo.from_json(User, {
        '$select': 'id, nickname, token',
        'token.in': json.dumps(['aabb', '22'])
    }, from_http_query=True)

    assert q.conditions.items[0].value[0] == b'\xaa\xbb'

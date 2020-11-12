import binascii
import json
from typing import Any, Union, List

from pycrud.pydantic_ext.hex_string import HexString
from pycrud.query import QueryInfo
from pycrud.types import RecordMapping, RecordMappingField


class User(RecordMapping):
    id: int
    nickname: str
    username: str
    password: str
    values: List[HexString] = []


def test_query_select_exclude():
    q = QueryInfo.from_table_raw(User, select=[User.id, User.nickname, User.password], select_exclude=[User.nickname])
    assert q.select_for_crud == [User.id, User.password]


def test_values_bug_2():
    qi = QueryInfo.from_json(User, {
        'values.contains': json.dumps(["5ef99253000000041d4164ef"])
    }, from_http_query=True)

    assert qi.conditions.items[0].value[0] == binascii.unhexlify('5ef99253000000041d4164ef')

from typing import Optional

from pydantic import Field

from pycurd.types import RecordMapping
from pycurd.values import ValuesToWrite


class User(RecordMapping):
    id: Optional[int]
    nickname: str
    test: int = 111


def test_values_bug_1():
    v = ValuesToWrite({
        'nickname': 'aaa'
    })
    v.bind(False, User)
    assert 'test' not in v

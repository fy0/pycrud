from typing import Optional, List

from pydantic import Field

from pycurd.types import RecordMapping
from pycurd.values import ValuesToWrite, ValuesDataFlag


class User(RecordMapping):
    id: Optional[int]
    nickname: str
    test: int = 111
    arr: List[str] = Field(default_factory=lambda: [])


def test_values_bug_1():
    v = ValuesToWrite({
        'nickname': 'aaa'
    })
    v.bind(False, User)
    assert 'test' not in v


def test_values_array_extend():
    v = ValuesToWrite({
        'arr.array_extend': ['aa', 'bb']
    }, table=User, try_parse=True)
    assert v.data_flag['arr'] == ValuesDataFlag.ARRAY_EXTEND

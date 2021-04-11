from typing import Optional, List

from pydantic import Field

from pycrud.types import Entity
from pycrud.values import ValuesToUpdate, ValuesDataUpdateFlag, ValuesToCreate


class User(Entity):
    id: Optional[int]
    nickname: str
    test: int = 111
    arr: List[str] = Field(default_factory=lambda: [])


def test_values_bug_1():
    v = ValuesToUpdate({
        'nickname': 'aaa'
    })
    v.bind(User)
    assert 'test' not in v


def test_values_array_extend():
    v = ValuesToUpdate({
        'arr.array_extend': ['aa', 'bb']
    }, entity=User).bind()
    assert v.data_flag['arr'] == ValuesDataUpdateFlag.ARRAY_EXTEND


def test_values_try_bind():
    # TODO: try bind 不存在了 但之前为什么会有这个阶段？
    v = ValuesToUpdate({
        'aaa': 'bbb',
        'arr.array_extend': ['aa', 'bb']
    }, entity=User).bind()
    assert 'aaa' not in v

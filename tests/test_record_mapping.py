from typing import Optional

import pytest
from pycrud.types import Entity, IDList


def test_record_mapping_clsmethod():
    with pytest.raises(AssertionError):
        class A(Entity):
            id: Optional[int]

            def on_update(cls, info, values, when_before_update, when_complete, perm=None):
                pass

    with pytest.raises(AssertionError):
        class A2(Entity):
            id: Optional[int]

            async def on_update(cls, info, values, when_before_update, when_complete, perm=None):
                pass

    with pytest.raises(AssertionError):
        class A3(Entity):
            id: Optional[int]

            @classmethod
            def on_update(cls, info, values, when_before_update, when_complete, perm=None):
                pass

    class A4(Entity):
        id: Optional[int]

        @classmethod
        async def on_update(cls, info, values, when_before_update, when_complete, perm=None):
            pass

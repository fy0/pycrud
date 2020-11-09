from typing import Optional

from pycurd.permission import RoleDefine, TablePerm, A
from pycurd.types import RecordMapping


class User(RecordMapping):
    id: Optional[str]


def test_role_delete_inherit():
    user1 = RoleDefine({
        User: TablePerm({
            User.id: {A.READ, A.QUERY}
        })
    })

    user2 = RoleDefine({
        User: TablePerm({
            User.id: {A.READ, A.QUERY}
        }, allow_delete=True)
    })

    user1_1 = RoleDefine({}, based_on=user1)
    user2_1 = RoleDefine({}, based_on=user2)
    user2_1_1 = RoleDefine({}, based_on=user2_1)

    assert user1_1.can_delete(User) == False
    assert user2.can_delete(User)
    assert user2_1.can_delete(User)
    assert user2_1_1.can_delete(User)

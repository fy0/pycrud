from typing import Optional

from pycrud.permission import RoleDefine, TablePerm, A
from pycrud.types import Entity


class User(Entity):
    id: Optional[str]


def test_role_delete_inherit():
    user1 = RoleDefine('user1', {
        User: TablePerm({
            User.id: {A.READ, A.QUERY}
        })
    })

    user2 = RoleDefine('user2', {
        User: TablePerm({
            User.id: {A.READ, A.QUERY}
        }, allow_delete=True)
    })

    user1_1 = RoleDefine('user1_1', {}, based_on=user1)
    user2_1 = RoleDefine('user2_1', {}, based_on=user2)
    user2_1_1 = RoleDefine('user2_1_1', {}, based_on=user2_1)

    user1.bind()
    user2.bind()
    user1_1.bind()
    user2_1.bind()
    user2_1_1.bind()

    assert user1_1.can_delete(User) == False
    assert user2.can_delete(User)
    assert user2_1.can_delete(User)
    assert user2_1_1.can_delete(User)

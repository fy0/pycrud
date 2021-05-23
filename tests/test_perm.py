from pycrud.permission import RoleDefine, TablePerm, A
from pycrud.types import Entity


def test_role_perm_simple():
    class User(Entity):
        id: int

    rp = RoleDefine('test', {
        User: TablePerm({
            User.id: {A.UPDATE},
        })
    })
    rp.bind()

    assert rp._ability_table[User][A.UPDATE] == {User.id}


def test_role_perm_default_and_append():
    class User(Entity):
        id: int
        time: int
        gender: str

    class Test(Entity):
        id: str

    rp = RoleDefine('test', {
        User: TablePerm({
            User.id: {A.UPDATE},
            User.time: {A.READ}
        },
            default_perm={A.READ, A.QUERY},
            append_perm={A.UPDATE}
        )
    })
    rp.bind()

    assert rp._ability_table[User][A.READ] == {User.time, User.gender}
    assert rp._ability_table[User][A.UPDATE] == {User.id, User.time, User.gender}
    assert rp._ability_table[User][A.QUERY] == {User.gender}

    assert rp.get_perm_avail(User, A.UPDATE) == {User.id, User.time, User.gender}
    assert rp.get_perm_avail(Test, A.UPDATE) == set()


def test_role_perm_based_on():
    class User(Entity):
        id: int
        time: int
        gender: str

    rp0 = RoleDefine('test', {
        User: TablePerm({
            User.id: {A.UPDATE},
            User.time: {A.READ}
        },
            default_perm={A.READ, A.QUERY},
            append_perm={A.UPDATE}
        )
    })

    rp = RoleDefine('test2', {
        User: TablePerm({
            User.id: {A.READ},
            User.time: {A.READ}
        },
            append_perm={A.UPDATE}
        )
    }, rp0)

    rp0.bind()
    rp.bind()

    assert rp._ability_table[User][A.READ] == {User.id, User.time, User.gender}
    assert rp._ability_table[User][A.UPDATE] == {User.id, User.time, User.gender}
    assert rp._ability_table[User][A.QUERY] == {User.gender}

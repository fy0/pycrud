from pycurd.permission import RoleDefine, TablePerm, A
from pycurd.types import RecordMapping


def test_role_perm_simple():
    class User(RecordMapping):
        id: int

    rp = RoleDefine({
        User: TablePerm({
            User.id: {A.WRITE},
        })
    })

    assert rp._ability_table[User][A.WRITE] == {User.id}


def test_role_perm_default_and_append():
    class User(RecordMapping):
        id: int
        time: int
        gender: str

    class Test(RecordMapping):
        id: str

    rp = RoleDefine({
        User: TablePerm({
            User.id: {A.WRITE},
            User.time: {A.READ}
        },
            default_perm={A.READ, A.QUERY},
            append_perm={A.WRITE}
        )
    })

    assert rp._ability_table[User][A.READ] == {User.time, User.gender}
    assert rp._ability_table[User][A.WRITE] == {User.id, User.time, User.gender}
    assert rp._ability_table[User][A.QUERY] == {User.gender}

    assert rp.get_perm_avail(User, A.WRITE) == {User.id, User.time, User.gender}
    assert rp.get_perm_avail(Test, A.WRITE) == set()


def test_role_perm_based_on():
    class User(RecordMapping):
        id: int
        time: int
        gender: str

    rp0 = RoleDefine({
        User: TablePerm({
            User.id: {A.WRITE},
            User.time: {A.READ}
        },
            default_perm={A.READ, A.QUERY},
            append_perm={A.WRITE}
        )
    })

    rp = RoleDefine({
        User: TablePerm({
            User.id: {A.READ},
            User.time: {A.READ}
        },
            append_perm={A.WRITE}
        )
    }, rp0)

    assert rp._ability_table[User][A.READ] == {User.id, User.time, User.gender}
    assert rp._ability_table[User][A.WRITE] == {User.id, User.time, User.gender}
    assert rp._ability_table[User][A.QUERY] == {User.gender}

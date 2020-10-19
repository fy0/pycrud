import pytest

from querylayer.crud.base_crud import PermInfo
from querylayer.crud.ext.peewee_crud import PeeweeCrud
from querylayer.crud.query_result_row import QueryResultRow
from querylayer.error import PermissionException
from querylayer.permission import RoleDefine, TablePerm, A
from querylayer.query import QueryInfo
from querylayer.values import ValuesToWrite
from tests.test_crud import crud_db_init, User

pytestmark = [pytest.mark.asyncio]


async def test_curd_perm_read():
    db, MUsers, MTopics, MTopics2 = crud_db_init()

    permission = {
        'visitor': RoleDefine({
            User: TablePerm({
                User.id: {A.READ},
                User.password: {A.READ}
            })
        }, match=None),
    }

    c = PeeweeCrud(permission, {User: MUsers}, db)
    info = QueryInfo.from_json(User, {})

    ret = await c.get_list_with_perm(info, perm=PermInfo(True, None, permission['visitor']))
    for i in ret:
        assert i.to_dict().keys() == {'id', 'password'}


async def test_curd_perm_query_disallow_and_allow_simple():
    db, MUsers, MTopics, MTopics2 = crud_db_init()

    permission = {
        'visitor': RoleDefine({
            User: TablePerm({
                User.id: {A.READ},
                User.password: {A.READ}
            })
        }, match=None),
        'user': RoleDefine({
            User: TablePerm({
                User.id: {A.READ, A.QUERY},
                User.password: {A.READ}
            })
        }),
    }

    c = PeeweeCrud(permission, {User: MUsers}, db)
    info = QueryInfo.from_json(User, {
        'id.eq': 5,
    })

    ret = await c.get_list_with_perm(info, perm=PermInfo(True, None, permission['visitor']))
    assert len(ret) == 5

    # 注意这里，权限过滤会改变info内部的样子
    info = QueryInfo.from_json(User, {
        'id.eq': 5,
    })
    ret = await c.get_list_with_perm(info, perm=PermInfo(True, None, permission['user']))
    assert len(ret) == 1


async def test_curd_perm_query_inside():
    pass


async def test_curd_perm_write():
    db, MUsers, MTopics, MTopics2 = crud_db_init()

    permission = {
        'visitor': RoleDefine({
            User: TablePerm({
                User.id: {A.READ, A.QUERY},
                User.nickname: {A.READ},
                User.password: {A.READ}
            })
        }, match=None),
        'user': RoleDefine({
            User: TablePerm({
                User.id: {A.READ, A.QUERY},
                User.nickname: {A.READ, A.WRITE},
                User.password: {A.READ}
            })
        }, match=None)
    }

    c = PeeweeCrud(permission, {User: MUsers}, db)

    # perm visitor
    ret = await c.update_with_perm(
        QueryInfo.from_json(User, {'id.eq': 5}),
        ValuesToWrite(User).parse({'nickname': 'aaa'}),
        perm=PermInfo(True, None, permission['visitor'])
    )
    assert len(ret) == 0  # all filtered

    # not check
    ret = await c.update_with_perm(
        QueryInfo.from_json(User, {'id.eq': 5}),
        ValuesToWrite(User).parse({'nickname': 'aaa'}),
        perm=PermInfo(False, None, permission['visitor'])
    )
    assert len(ret) == 1
    assert ret[0] == 5

    # perm user
    ret = await c.update_with_perm(
        QueryInfo.from_json(User, {'id.eq': 5}),
        ValuesToWrite(User).parse({'nickname': 'ccc'}),
        perm=PermInfo(True, None, permission['user'])
    )
    assert len(ret) == 1
    assert ret[0] == 5

    # returning
    ret = await c.update_with_perm(
        QueryInfo.from_json(User, {'id.eq': 5}),
        ValuesToWrite(User).parse({'nickname': 'ccc'}),
        perm=PermInfo(True, None, permission['user']),
        returning=True
    )
    assert len(ret) == 1
    assert isinstance(ret[0], QueryResultRow)


async def test_curd_perm_delete():
    db, MUsers, MTopics, MTopics2 = crud_db_init()

    role_visitor = RoleDefine({
        User: TablePerm({
            User.id: {A.READ, A.QUERY},
            User.nickname: {A.READ},
            User.password: {A.READ}
        })
    }, match=None)

    role_user = RoleDefine({
        User: TablePerm({
            User.id: {A.READ, A.QUERY},
            User.nickname: {A.READ, A.WRITE},
            User.password: {A.READ}
        }, allow_delete=True)
    }, match=None)

    c = PeeweeCrud(None, {User: MUsers}, db)

    # perm visitor
    with pytest.raises(PermissionException):
        await c.delete_with_perm(
            QueryInfo.from_json(User, {}),
            perm=PermInfo(True, None, role_visitor)
        )

    # perm user
    assert len(await c.get_list(QueryInfo(User))) == 5
    ret = await c.delete_with_perm(
        QueryInfo.from_json(User, {}),
        perm=PermInfo(True, None, role_user)
    )
    assert len(ret) == 5
    assert len(await c.get_list(QueryInfo(User))) == 0


async def test_curd_perm_insert():
    db, MUsers, MTopics, MTopics2 = crud_db_init()

    role_visitor = RoleDefine({
        User: TablePerm({
            User.id: {A.READ, A.QUERY},
            User.nickname: {A.READ},
            User.password: {A.READ}
        })
    }, match=None)

    role_user = RoleDefine({
        User: TablePerm({
            User.id: {A.READ, A.QUERY},
            User.username: {A.CREATE},
            User.nickname: {A.READ, A.WRITE, A.CREATE},
            User.password: {A.READ, A.CREATE}
        }, allow_delete=True)
    }, match=None)

    c = PeeweeCrud(None, {User: MUsers}, db)

    # perm visitor
    # 注：这里存在问题，权限检查过后，过滤掉部分列应再次检查data model
    ret = await c.insert_many_with_perm(
        User,
        [ValuesToWrite(User).parse({'id': 10, 'nickname': 'aaa'})],
        perm=PermInfo(True, None, role_visitor)
    )
    assert len(ret) == 0  # all filtered

    # perm user
    ret = await c.insert_many_with_perm(
        User,
        [ValuesToWrite(User).parse({'id': 10, 'nickname': 'aaa', 'username': 'u1'}, check_insert=True)],
        perm=PermInfo(True, None, role_user)
    )
    assert len(ret) == 1

    ret2 = await c.get_list(QueryInfo.from_json(User, {'id.eq': ret[0]}))
    assert ret2[0].to_dict()['id'] == ret[0]

    # perm not check
    ret = await c.insert_many_with_perm(
        User,
        [ValuesToWrite(User, {'nickname': 'qqqq', 'username': 'u1'}, check_insert=True)],
        perm=PermInfo(False, None, role_visitor)
    )
    assert len(ret) == 1

    # with returning
    ret = await c.insert_many_with_perm(
        User,
        [ValuesToWrite(User, {'nickname': 'wwww', 'username': 'u2'}, check_insert=True)],
        perm=PermInfo(False, None, role_visitor),
        returning=True
    )

    assert len(ret) == 1
    d = ret[0].to_dict()
    assert d['username'] == 'u2'
    assert d['nickname'] == 'wwww'

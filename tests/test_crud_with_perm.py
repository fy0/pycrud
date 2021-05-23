import pytest
from pydantic import ValidationError

from pycrud.crud.ext.peewee_crud import PeeweeCrud
from pycrud.crud.query_result_row import QueryResultRow
from pycrud.error import PermissionException, InvalidQueryValue
from pycrud.permission import RoleDefine, TablePerm, A, PermInfo
from pycrud.query import QueryInfo
from pycrud.values import ValuesToUpdate, ValuesToCreate
from tests.test_crud import crud_db_init, User

pytestmark = [pytest.mark.asyncio]


async def test_crud_perm_read():
    db, MUsers, MTopics, MTopics2 = crud_db_init()

    visitor = RoleDefine('visitor', {
        User: TablePerm({
            User.id: {A.READ},
            User.password: {A.READ}
        })
    })

    c = PeeweeCrud([visitor], {User: MUsers}, db)
    info = QueryInfo.from_json(User, {})

    ret = await c.get_list_with_perm(info, perm=PermInfo(None, visitor))
    for i in ret:
        assert i.to_dict().keys() == {'id', 'password'}


async def test_crud_perm_query_disallow_and_allow_simple():
    db, MUsers, MTopics, MTopics2 = crud_db_init()

    visitor = RoleDefine('visitor', {
        User: TablePerm({
            User.id: {A.READ},
            User.password: {A.READ}
        })
    })

    user = RoleDefine('user', {
        User: TablePerm({
            User.id: {A.READ, A.QUERY},
            User.password: {A.READ}
        })
    })

    c = PeeweeCrud([visitor, user], {User: MUsers}, db)
    info = QueryInfo.from_json(User, {
        'id.eq': 5,
    })

    ret = await c.get_list_with_perm(info, perm=PermInfo(None, visitor))
    assert len(ret) == 5

    # 注意这里，权限过滤会改变info内部的样子
    info = QueryInfo.from_json(User, {
        'id.eq': 5,
    })
    ret = await c.get_list_with_perm(info, perm=PermInfo(None, user))
    assert len(ret) == 1


async def test_crud_perm_query_inside():
    pass


async def test_crud_perm_write():
    db, MUsers, MTopics, MTopics2 = crud_db_init()

    visitor = RoleDefine('visitor', {
        User: TablePerm({
            User.id: {A.READ, A.QUERY},
            User.nickname: {A.READ},
            User.password: {A.READ}
        })
    })

    user = RoleDefine('user', {
        User: TablePerm({
            User.id: {A.READ, A.QUERY},
            User.nickname: {A.READ, A.UPDATE},
            User.password: {A.READ}
        })
    })

    c = PeeweeCrud([visitor, user], {User: MUsers}, db)

    # perm visitor
    with pytest.raises(InvalidQueryValue):
        ret = await c.update_with_perm(
            QueryInfo.from_json(User, {'id.eq': 5}),
            ValuesToUpdate({'nickname': 'aaa'}, User).bind(),
            perm=PermInfo(True, None, visitor)
        )
        assert len(ret) == 0  # all filtered

    # skip permission check
    ret = await c.update_with_perm(
        QueryInfo.from_json(User, {'id.eq': 5}),
        ValuesToUpdate({'nickname': 'aaa'}, User).bind(),
        perm=PermInfo(None, visitor, skip_check=True)
    )
    assert len(ret) == 1
    assert ret[0] == 5

    # perm user
    ret = await c.update_with_perm(
        QueryInfo.from_json(User, {'id.eq': 5}),
        ValuesToUpdate({'nickname': 'ccc'}, User).bind(),
        perm=PermInfo(None, user)
    )
    assert len(ret) == 1
    assert ret[0] == 5

    # returning
    ret = await c.update_with_perm(
        QueryInfo.from_json(User, {'id.eq': 5}),
        ValuesToUpdate({'nickname': 'ccc'}, User).bind(),
        perm=PermInfo(None, user),
        returning=True
    )
    assert len(ret) == 1
    assert isinstance(ret[0], QueryResultRow)


async def test_crud_perm_delete():
    db, MUsers, MTopics, MTopics2 = crud_db_init()

    role_visitor = RoleDefine('visitor', {
        User: TablePerm({
            User.id: {A.READ, A.QUERY},
            User.nickname: {A.READ},
            User.password: {A.READ}
        })
    })

    role_user = RoleDefine('user', {
        User: TablePerm({
            User.id: {A.READ, A.QUERY},
            User.nickname: {A.READ, A.UPDATE},
            User.password: {A.READ}
        }, allow_delete=True)
    })

    c = PeeweeCrud([role_user, role_visitor], {User: MUsers}, db)

    # perm visitor
    with pytest.raises(PermissionException):
        await c.delete_with_perm(
            QueryInfo.from_json(User, {}),
            perm=PermInfo(None, role_visitor)
        )

    # perm user
    assert len(await c.get_list(QueryInfo(User))) == 5
    ret = await c.delete_with_perm(
        QueryInfo.from_json(User, {}),
        perm=PermInfo(None, role_user)
    )
    assert len(ret) == 5
    assert len(await c.get_list(QueryInfo(User))) == 0


async def test_crud_perm_insert():
    db, MUsers, MTopics, MTopics2 = crud_db_init()

    role_visitor = RoleDefine('visitor', {
        User: TablePerm({
            User.id: {A.READ, A.QUERY},
            User.nickname: {A.READ},
            User.password: {A.READ}
        })
    })

    role_user = RoleDefine('user', {
        User: TablePerm({
            User.id: {A.READ, A.QUERY},
            User.username: {A.CREATE},
            User.nickname: {A.READ, A.UPDATE, A.CREATE},
            User.password: {A.READ, A.CREATE}
        }, allow_delete=True)
    })

    c = PeeweeCrud([role_user, role_visitor], {User: MUsers}, db)

    # perm visitor
    with pytest.raises(ValidationError):
        ret = await c.insert_many_with_perm(
            User,
            [ValuesToCreate({'id': 10, 'nickname': 'aaa', 'username': 'bbb'}, User)],
            perm=PermInfo(None, role_visitor)
        )
        assert len(ret) == 0  # all filtered

    # perm user
    ret = await c.insert_many_with_perm(
        User,
        [ValuesToCreate({'id': 10, 'nickname': 'aaa', 'username': 'u1'})],
        perm=PermInfo(None, role_user)
    )
    assert len(ret) == 1

    ret2 = await c.get_list(QueryInfo.from_json(User, {'id.eq': ret[0]}))
    assert ret2[0].to_dict()['id'] == ret[0]

    # perm not check
    ret = await c.insert_many_with_perm(
        User,
        [ValuesToCreate({'nickname': 'qqqq', 'username': 'u1'}, User).bind()],
        perm=PermInfo(None, role_visitor, skip_check=True)
    )
    assert len(ret) == 1

    # with returning
    ret = await c.insert_many_with_perm(
        User,
        [ValuesToCreate({'nickname': 'wwww', 'username': 'u2'}, User).bind()],
        perm=PermInfo(None, role_visitor, skip_check=True),
        returning=True
    )

    assert len(ret) == 1
    d = ret[0].to_dict()
    assert d['username'] == 'u2'
    assert d['nickname'] == 'wwww'

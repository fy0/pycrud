import uvicorn

from typing import Optional
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware

from pycrud import Entity, QueryResultRow, QueryInfo, ValuesToUpdate
from pycrud.permission import RoleDefine, TablePerm, A, PermInfo
from pycrud.crud.ext.peewee_crud import PeeweeCrud
from pycrud.helpers.fastapi_ext import PermissionDependsBuilder

from examples.model_peewee import db, UserModel, TopicModel


# Crud Initialize
from pycrud.utils import UserObject


class User(Entity):
    id: Optional[int]
    nickname: str
    is_admin: bool
    password: str = 'password'

    @classmethod
    async def on_query(cls, info: 'QueryInfo', perm: 'PermInfo' = None):
        # 当申请 member:self 权限时，只能修改自己
        if perm and perm.role.name == 'member:self':
            info.select.append(cls.id == perm.user.id)


class Topic(Entity):
    id: Optional[int]
    title: str
    user_id: int
    content: str

    @classmethod
    async def on_query(cls, info: 'QueryInfo', perm: 'PermInfo' = None):
        # 当申请 member:self 权限时，只能选取到自己发的文章
        if perm and perm.role.name == 'member:self':
            info.select.append(cls.user_id == perm.user.id)


roles = [
    # 游客，可以阅读文章，查看作者，根据作者找文章，创建新用户。
    # 第一个角色会成为默认角色
    RoleDefine('visitor', {
        User: TablePerm({
            User.id: {A.READ, A.QUERY},
            User.nickname: {A.READ, A.CREATE},  # create 为创建权限，意为调用创建接口时，能够指定这列的值。
        }),
        Topic: TablePerm({
            Topic.id: {A.READ, A.QUERY},
            Topic.title: {A.READ},
            Topic.user_id: {A.READ, A.QUERY},  # query 允许以user_id为凭据查找文章
            Topic.content: {A.READ},
        })
    }),

    # 会员，在游客权限基础上可以发布文章
    RoleDefine('member', {
        Topic: TablePerm({
            Topic.title: {A.READ, A.CREATE},
            Topic.content: {A.READ, A.CREATE},
        })
    }, based_on='visitor'),  # 基于游客权限

    # 会员权限(对于自己)，可以修改自己的昵称，修改和删除自己的文章
    # 完全可以写在member角色里，这里拆分出来是为了清晰
    RoleDefine('member:self', {
        User: TablePerm({
            User.nickname: {A.READ, A.UPDATE},  # update为修改权限
        }),
        Topic: TablePerm({
            Topic.title: {A.READ, A.UPDATE},
            Topic.content: {A.READ, A.UPDATE},
        }, allow_delete=True)  # 可删除
    }, based_on='member'),

    # 管理员，有全部权限，开发初期阶段可以通过这种形式省事
    RoleDefine('admin', {
        User: TablePerm({}, default_perm={A.QUERY, A.CREATE, A.READ, A.UPDATE}, allow_delete=True),
        Topic: TablePerm({}, default_perm={A.QUERY, A.CREATE, A.READ, A.UPDATE}, allow_delete=True),
    })
]

# entities 对 Model 的映射
entities_to_table = {
    User: UserModel,
    Topic: TopicModel
}

c = PeeweeCrud(roles, entities_to_table, db)


# Web Service

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


class PDB(PermissionDependsBuilder):
    @classmethod
    async def get_user(cls, request: Request):
        ret = await c.get_list(QueryInfo.from_table(User, where=[User.nickname == request.query_params.get('name')]))
        if ret:
            return ret[0]

    @classmethod
    async def validate_role(cls, user: User, current_request_role: str) -> RoleDefine:
        if user:
            if user.is_admin:
                if current_request_role in {'member', 'member:self', 'admin'}:
                    return c.permission.get(current_request_role)
            else:
                if current_request_role in {'member', 'member:self'}:
                    return c.permission.get(current_request_role)

        # 游客
        return c.default_role


@app.post("/user/create", response_model=User.dto.resp_create())
async def user_create(item: User.dto.get_create(), perm=PDB.perm_info_depends()):
    """ 创建用户 role(visitor) """
    return await c.insert_many_with_perm(User, [item], perm=perm)  # response id list: [1]


@app.get("/topic/list", response_model=Topic.dto.resp_list())
async def topic_list(
        q=PDB.query_info_depends(Topic),
        perm=PDB.perm_info_depends()
):
    """ 获取文章列表 role(visitor) """
    topics = await c.get_list(q)

    def solve(x: QueryResultRow):
        val = x.to_dict()
        return dict(Topic.dto.get_read(perm.role).parse_obj(val))

    return [solve(x) for x in topics]


@app.post("/topic/update", response_model=User.dto.resp_update())
async def topic_update(
        item: Topic.dto.get_update('member:self'),  # 修改内容
        q=PDB.query_info_depends(Topic, 'member:self'),  # 指定文章
        perm=PDB.perm_info_depends('member:self')  # 如果访问者没有 member 角色，会校验失败
):
    """ 更新文章 role(member:self) """
    return await c.update_with_perm(q, ValuesToUpdate(item), perm=perm)  # response id list: [1]


@app.post("/topic/delete", response_model=Topic.dto.resp_delete())
async def topic_delete(
        q=PDB.query_info_depends(Topic, 'member:self'), # 指定文章
        perm=PDB.perm_info_depends('member:self')
):
    """ 删除文章 role(member:self) """
    return await c.delete_with_perm(q, perm=perm)  # response id list: [1]


print('Service Running ...')
uvicorn.run(app, host='0.0.0.0', port=3000)

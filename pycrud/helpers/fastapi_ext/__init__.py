from abc import abstractmethod
from typing import Type, Any, Union

from fastapi import Request, HTTPException, Query, Depends
from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError
from pydantic.main import BaseModel

from pycrud import QueryInfo
from pycrud.permission import PermInfo, RoleDefine
from pycrud.types import Entity
from pycrud.utils import sentinel, UserObject


class PermissionDependsBuilder:
    @classmethod
    @abstractmethod
    async def validate_role(cls, user: UserObject, current_request_role: str) -> RoleDefine:
        """
        Validate if the role is owned current user
        :param user:
        :param current_request_role:
        :return:
        """
        pass

    @classmethod
    @abstractmethod
    async def get_user(cls, request: Request) -> UserObject:
        """
        get current user
        :param request:
        :return: User Object
        """
        pass

    @classmethod
    def perm_info_depends(cls, request_role: str = sentinel) -> PermInfo:

        async def get_perm_info(request: Request) -> PermInfo:
            """
            depends functon, return a PermInfo object
            :param request:
            :return:
            """
            user = await cls.get_user(request)
            role = await cls.validate_role(user, request_role)
            return PermInfo(user, role)

        return Depends(get_perm_info)

    @classmethod
    def query_info_depends(cls, entity: Type[Entity], request_role: str = sentinel):
        async def get_query_info(request: Request) -> QueryInfo:
            # fastapi 不支持部分json schema语法
            return QueryInfo.from_json(entity, request.query_params, from_http_query=True)

        from inspect import Parameter, Signature

        def make_param(key, type_):
            key2 = key.replace('.{op}', '_op')
            return Parameter(key2, Parameter.KEYWORD_ONLY, annotation=Any, default=Query(None, alias=key))

        doc_model = entity.dto.get_query_for_doc(request_role)
        params = [
            Parameter('request', Parameter.POSITIONAL_OR_KEYWORD, annotation=Request),
            # *[make_param(k, v) for k, v in doc_model.__fields__.items()],
        ]

        get_query_info.__signature__ = Signature(params)

        return Depends(get_query_info)

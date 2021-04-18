from abc import abstractmethod
from typing import Type, Any, Union

from fastapi import Request, HTTPException, Query, Depends
from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError
from pydantic.main import BaseModel

from pycrud.crud.base_crud import PermInfo
from pycrud.types import Entity


def QueryDto(e: Type[Entity], pdb=None):
    """
    Query Validator loader for PyDantic
    :param e:
    :return:
    """
    from inspect import Parameter, Signature

    def query_wrap(model: BaseModel):
        def depends_func(request: Request, **kwargs):
            role = pdb.get_role(request) if pdb else None

            try:
                return dict(e.dto.get_query(role, from_http_query=True).parse_obj(request.query_params))
            except ValidationError as err:
                raise HTTPException(status_code=422, detail=jsonable_encoder(err.errors()))

        def make_param(key, type_):
            key2 = key.replace('.{op}', '_op')
            return Parameter(key2, Parameter.KEYWORD_ONLY, annotation=Any, default=Query(None, alias=key))

        params = [
            Parameter('request', Parameter.POSITIONAL_OR_KEYWORD, annotation=Request),
            *[make_param(k, v) for k, v in model.__fields__.items()],
        ]

        depends_func.__signature__ = Signature(params)
        return depends_func

    return Depends(query_wrap(e.dto.get_query_for_doc()))


class PermissionDependsBuilder:
    @classmethod
    @abstractmethod
    def validate_role(self, current_request_role: str):
        """
        Validate if the role is owned current user
        :param current_request_role:
        :return:
        """
        pass

    @classmethod
    @abstractmethod
    def get_user(cls, request: Request):
        """
        depends function, get current user
        :param request:
        :return:
        """
        pass

    @classmethod
    def get_role(cls, request: Request) -> Union[None, str]:
        """
        depends function, get current role key
        :param request:
        :return:
        """
        r = request.headers.get('role')

        if cls.validate_role(r):
            return r

    @classmethod
    def get_perm_info(cls, request: Request) -> PermInfo:
        """
        depends functon, return a PermInfo object
        :param request:
        :return:
        """
        return PermInfo(True, cls.get_user(request), cls.get_role(request))

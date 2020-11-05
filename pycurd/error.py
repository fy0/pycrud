
class PyCrudException(Exception):
    pass


class DBException(PyCrudException):
    pass


class PermissionException(PyCrudException):
    pass


class InvalidQueryConditionColumn(PyCrudException):
    pass


class InvalidQueryConditionValue(PyCrudException):
    pass


class UnknownQueryOperator(PyCrudException):
    pass


class InvalidOrderSyntax(PyCrudException):
    pass


class UnsupportedQueryOperator(PyCrudException):
    pass

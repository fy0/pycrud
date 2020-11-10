
class PyCrudException(Exception):
    pass


class DBException(PyCrudException):
    pass


class PermissionException(PyCrudException):
    pass


class UnknownDatabaseException(PyCrudException):
    pass


class InvalidQueryConditionColumn(PyCrudException):
    pass


class InvalidQueryConditionOperator(PyCrudException):
    pass


class InvalidQueryConditionValue(PyCrudException):
    pass


class UnknownQueryOperator(PyCrudException):
    pass


class InvalidQueryValue(PyCrudException):
    pass


class InvalidOrderSyntax(PyCrudException):
    pass


class UnsupportedQueryOperator(PyCrudException):
    pass

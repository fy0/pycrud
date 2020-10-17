
class QueryLayerException(Exception):
    pass


class PermissionException(QueryLayerException):
    pass


class InvalidQueryConditionValue(QueryLayerException):
    pass


class UnknownQueryOperator(QueryLayerException):
    pass


class UnsupportedQueryOperator(QueryLayerException):
    pass

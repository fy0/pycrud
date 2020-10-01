
class DataLayerException(Exception):
    pass


class InvalidQueryConditionValue(DataLayerException):
    pass


class UnknownQueryOperator(DataLayerException):
    pass


class UnsupportedQueryOperator(DataLayerException):
    pass

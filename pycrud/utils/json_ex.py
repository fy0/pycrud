import binascii
import json

from pycrud.crud.query_result_row import QueryResultRow


def json_default_ex(o):
    if isinstance(o, memoryview):
        return o.hex()
    elif isinstance(o, bytes):
        return str(binascii.hexlify(o), 'utf-8')
    elif isinstance(o, set):
        return list(o)
    elif isinstance(o, QueryResultRow):
        return o.to_dict()


def json_dumps_ex(obj, **kwargs):
    return json.dumps(obj, default=json_default_ex, **kwargs)

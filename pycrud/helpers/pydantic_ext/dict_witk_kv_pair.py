import json
import sys
from typing import Dict, Generic, TypeVar, Tuple, Any, Mapping, Union, Set

from pydantic.error_wrappers import ErrorWrapper
from pydantic.fields import ModelField
from pydantic import BaseModel, ValidationError, constr
from pydantic.generics import GenericModel

try:
    from typing import get_origin
except ImportError:
    from typing_extensions import get_origin


TKeyType = TypeVar('TKeyType', bound=str)
TValueType = TypeVar('TValueType')


class KVPair(BaseModel, Generic[TKeyType, TValueType]):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v: Tuple[TKeyType, TValueType], field: ModelField):
        f_key: ModelField = field.sub_fields[0]
        f_value: ModelField = field.sub_fields[1]

        v = cls.value_solve(v)
        val_key, err_key = f_key.validate(v[0], None, loc='key')
        if err_key: raise ValidationError([err_key], cls)

        val_value, err_value = f_value.validate(v[1], None, loc='value')
        if err_value: raise ValidationError([err_value], cls)

        return val_key, val_value

    @classmethod
    def value_solve(cls, v):
        return v


class HttpKVPair(KVPair, Generic[TKeyType, TValueType]):
    """
    value should be a json string, for works with request query.
    """
    @classmethod
    def value_solve(cls, v):
        try:
            v2 = json.loads(v[1])
        except (json.JSONDecodeError, TypeError) as e:
            raise ValidationError([ErrorWrapper(Exception("must be a json string"), loc="value")], model=cls)
        return v[0], v2


TKVPair = TypeVar('TKVPair')


class DictWithKVPair(BaseModel, Generic[TKVPair]):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, field: ModelField):
        if not isinstance(v, Mapping):
            raise TypeError('mapping required')

        generic_field: ModelField = field.sub_fields[0]
        items = []

        for i in v.items():
            val, error = generic_field.validate(i, None, loc=f'{i[0]}')  # loc=f'{field.name}.{i[0]}'
            if error:
                err_values = []
                for e in error:
                    e: ErrorWrapper
                    if e.exc.errors()[0]['loc'][0] == 'value':
                        err_values.append(e)
                if err_values:
                    # if key matched, show value error only
                    raise ValidationError(err_values, cls)
                else:
                    raise ValidationError(error, cls)
            items.append(val)

        return dict(items)


def kv_pair_monkey_patch():
    import pydantic.schema
    _field_type_schema = pydantic.schema.field_type_schema

    def _field_type_schema_wrap(field: ModelField, **kwargs) -> Tuple[Dict[str, Any], Dict[str, Any], Set[str]]:
        if field.type_ == DictWithKVPair:
            f_schema = {}

            def solve(f: ModelField):
                ret = []
                for sf in f.sub_fields:
                    o = get_origin(sf.type_)
                    if o == Union:
                        ret.extend(solve(sf))
                    elif o is None and sf.type_ == KVPair:
                        ret.append(sf)
                return ret

            sub_fields = solve(field)

            patternProperties = {}
            for i in sub_fields:
                i: ModelField
                f_key: ModelField = i.sub_fields[0]
                f_value: ModelField = i.sub_fields[1]

                k = _field_type_schema(f_key, **kwargs)[0]['pattern']
                patternProperties[k] = _field_type_schema(f_value, **kwargs)[0]

            f_schema.update({
                "patternProperties": patternProperties,
                "additionalProperties": False
            })

            return f_schema, {}, set()
        return _field_type_schema(field, **kwargs)

    pydantic.schema.field_type_schema = _field_type_schema_wrap


kv_pair_monkey_patch()


if __name__ == '__main__':
    class TestModel(BaseModel):
        __root__: DictWithKVPair[
            Union[
                KVPair[constr(regex="^S_"), str],
                KVPair[constr(regex="^I_"), int],
                KVPair[constr(regex="^id\\.(eq|ne|lt|le|ge|gt)(\\.\\d+)?$"), int],
                HttpKVPair[constr(regex="^name\\.(eq|ne|lt|le|ge|gt)(\\.\\d+)?$"), int],
            ]
        ]

    print(TestModel.parse_obj({"S_25": "This is a string", "I_2": 456}))
    print(TestModel.parse_obj({"S_25": 123, "I_2": 456, 'id.eq': 1, 'name.eq': '2'}))
    print(TestModel.schema())

    q: TestModel = TestModel.parse_obj({})
    print(q.dict())

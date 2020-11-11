import binascii


class HexString(bytes):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(
            pattern='^([A-Za-z0-9]{2})+$',
            examples=['aabb11', '1122', 'af02'],
        )

    @classmethod
    def validate(cls, v):
        if isinstance(v, bytes):
            return v
        elif isinstance(v, memoryview):
            return v.tobytes()
        elif isinstance(v, str):
            try:
                return cls(binascii.unhexlify(bytes(v, 'utf-8')))
            except Exception:
                raise ValueError('invalid hex string')

        raise ValueError('invalid type')

    def __repr__(self):
        return f'HexString({super().__repr__()})'

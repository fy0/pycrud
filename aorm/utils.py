import re


def get_class_full_name(cls):
    return '%s.%s' % (cls.__module__, cls.__qualname__)


def camel_case_to_underscore_case(raw_name):
    name = re.sub(r'([A-Z]{2,})', r'_\1', re.sub(r'([A-Z][a-z]+)', r'_\1', raw_name))
    if name.startswith('_'):
        name = name[1:]
    return name.lower()

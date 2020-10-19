from pycurd.utils.name_helper import get_class_full_name, camel_case_to_underscore_case


class A:
    pass


def test_get_class_full_name():
    assert get_class_full_name(A) == 'tests.test_utils_name_helper.A'


def test_camel_case_to_underscore_case():
    assert camel_case_to_underscore_case('Foobar') == 'foobar'
    assert camel_case_to_underscore_case('FooBar') == 'foo_bar'
    assert camel_case_to_underscore_case('FOOBar') == 'foo_bar'
    assert camel_case_to_underscore_case('fooBar') == 'foo_bar'
    assert camel_case_to_underscore_case('FOO') == 'foo'
    assert camel_case_to_underscore_case('FOoBar') == 'f_oo_bar'

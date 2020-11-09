from enum import Enum


class QUERY_OP_COMPARE(Enum):
    EQ = ('eq', '==')
    NE = ('ne', '!=')
    LT = ('lt', '<')
    LE = ('le', '<=')
    GE = ('ge', '>=')
    GT = ('gt', '>')


class QUERY_OP_LOGIC(Enum):
    AND = ('and',)
    OR = ('or',)


class QUERY_OP_RELATION(Enum):
    IN = ('in',)
    NOT_IN = ('notin', 'not in')
    IS = ('is',)
    IS_NOT = ('isnot', 'is not')
    PREFIX = ('prefix',)  # string like only
    IPREFIX = ('iprefix',)  # string like only
    CONTAINS = ('contains',)  # ArrayField only
    CONTAINS_ANY = ('contains_any',)  # ArrayField only


QUERY_OP_FROM_TXT = {}

for i in (QUERY_OP_COMPARE, QUERY_OP_RELATION):
    for j in i:
        for opval in j.value:
            QUERY_OP_FROM_TXT[opval] = j

'''
class QUERY_OP(Enum, QUERY_OP_LOGIC, QUERY_OP_COMPARE, QUERY_OP_RELATION):
    pass
'''

if __name__ == '__main__':
    def solve(e, t):
        for k in e:
            print('| %s | %s | %s |' % (t, k.name, k.name))

    print('| type | operator | text |')
    print('| ---- | -------- | ---- |')
    solve(QUERY_OP_COMPARE, 'compare')
    solve(QUERY_OP_RELATION, 'relation')
    solve(QUERY_OP_LOGIC, 'logic')

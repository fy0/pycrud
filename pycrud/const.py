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
    IS = ('is',)
    IS_NOT = ('isnot', 'is not')

    IN = ('in',)
    NOT_IN = ('notin', 'not in')

    # string like only
    PREFIX = ('prefix',)
    IPREFIX = ('iprefix',)

    # ArrayField only
    CONTAINS_ALL = ('contains_all', 'contains',)
    CONTAINS_ANY = ('contains_any',)


class OP_UPDATE(Enum):
    INCR = ('incr',)
    DECR = ('decr',)

    # ArrayField only
    ARRAY_EXTEND = ('array_extend',)
    ARRAY_PRUNE = ('array_prune',)

    ARRAY_EXTEND_DISTINCT = ('array_extend_distinct',)
    ARRAY_PRUNE_DISTINCT = ('array_prune_distinct',)


# value: column_type
OP_QUERY_TYPE_1 = {
    QUERY_OP_COMPARE.EQ, QUERY_OP_COMPARE.NE, QUERY_OP_COMPARE.LT, QUERY_OP_COMPARE.LE, QUERY_OP_COMPARE.GT, QUERY_OP_COMPARE.GE,
    QUERY_OP_RELATION.IS, QUERY_OP_RELATION.IS_NOT
}

# value: List[column_type]
OP_QUERY_TYPE_2 = {
    QUERY_OP_RELATION.IN, QUERY_OP_RELATION.NOT_IN
}

OP_QUERY_TYPE_ARRAY = {
    QUERY_OP_RELATION.CONTAINS_ALL, QUERY_OP_RELATION.CONTAINS_ANY
}

OP_QUERY_TYPE_STRING_LIKE = {
    QUERY_OP_RELATION.PREFIX, QUERY_OP_RELATION.IPREFIX
}

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

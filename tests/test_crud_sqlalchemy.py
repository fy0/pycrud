from typing import Optional

import pytest

from pycrud.const import QUERY_OP_COMPARE, QUERY_OP_RELATION
from pycrud.crud.ext.sqlalchemy_crud import SQLAlchemyCrud
from pycrud.crud.query_result_row import QueryResultRow
from pycrud.query import QueryInfo, QueryConditions, ConditionExpr
from pycrud.types import Entity
from pycrud.values import ValuesToUpdate, ValuesToCreate

pytestmark = [pytest.mark.asyncio]


class User(Entity):
    id: Optional[int]
    nickname: str
    username: str
    password: str = 'password'


class Topic(Entity):
    id: Optional[int]
    title: str
    user_id: int
    content: Optional[str] = None
    time: int


def crud_db_init():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import declarative_base, sessionmaker
    from sqlalchemy import Column, Integer, String, Sequence

    engine = create_engine("sqlite:///:memory:")
    Base = declarative_base()
    Session = sessionmaker(bind=engine)

    class Users(Base):
        __tablename__ = 'users'
        id = Column(Integer, Sequence('user_id_seq'), primary_key=True)
        username = Column(String, index=True)
        nickname = Column(String)
        password = Column(String)

    class Topics(Base):
        __tablename__ = 'topic'
        id = Column(Integer, Sequence('topic_id_seq'), primary_key=True)
        title = Column(String, index=True)
        time = Column(Integer)
        content = Column(String)
        user_id = Column(Integer)

    class Topics2(Base):
        __tablename__ = 'topic2'
        id = Column(Integer, Sequence('topic2_id_seq'), primary_key=True)
        title = Column(String(255), index=True)
        time = Column(Integer, index=True)
        content = Column(String)
        user_id = Column(Integer)

    Base.metadata.create_all(engine)

    session = Session()
    session.add(Users(username='test', nickname=2, password='pass'))
    session.add(Users(username='test2', nickname=2, password='pass'))
    session.add(Users(username='test3', nickname=2, password='pass'))
    session.add(Users(username='test4', nickname=2, password='pass'))
    session.add(Users(username='test5', nickname=2, password='pass'))

    session.add(Topics(title='test', time=1, content='content1', user_id=1))
    session.add(Topics(title='test2', time=1, content='content2', user_id=1))
    session.add(Topics(title='test3', time=1, content='content3', user_id=2))
    session.add(Topics(title='test4', time=1, content='content4', user_id=2))

    session.add(Topics2(title='test', time=1, content='content1', user_id=1))
    session.add(Topics2(title='test2', time=1, content='content2', user_id=1))
    session.add(Topics2(title='test3', time=1, content='content3', user_id=2))
    session.add(Topics2(title='test4', time=1, content='content4', user_id=2))

    session.commit()

    return engine, session, Users, Topics, Topics2


async def test_crud_simple():
    db, session, MUsers, MTopics, MTopics2 = crud_db_init()

    info = QueryInfo(User)
    info.select = [User.id, User.username, User.password, User.nickname]
    info.conditions = QueryConditions([])

    c = SQLAlchemyCrud(None, {
        User: 'users',
        Topic: 'topic',
    }, db)

    ret = await c.get_list(info)
    assert len(ret) == session.query(MUsers).count()

    for i in ret:
        assert isinstance(i, QueryResultRow)
        assert isinstance(i.id, int)

    info.conditions.items.append(ConditionExpr(User.id, QUERY_OP_COMPARE.EQ, 2))
    ret = await c.get_list(info)
    assert len(ret) == 1

    info.foreign_keys = {
        'topic[]': QueryInfo(Topic, [Topic.id, Topic.title, Topic.user_id], conditions=QueryConditions([
            ConditionExpr(Topic.user_id, QUERY_OP_RELATION.IN, [2, 3]),
        ])),
        'topic': QueryInfo(Topic, [Topic.id, Topic.title, Topic.user_id], conditions=QueryConditions([
            ConditionExpr(Topic.user_id, QUERY_OP_RELATION.IN, [2, 3]),
        ]), foreign_keys={
            'user': QueryInfo(User, [User.id, User.nickname], conditions=QueryConditions([
                ConditionExpr(Topic.user_id, QUERY_OP_COMPARE.EQ, User.id),
            ]))
        }),
    }

    ret = await c.get_list_with_foreign_keys(info)
    assert ret[0].id == 2
    d = ret[0].to_dict()

    assert d['$extra']['topic']['id'] == 3
    assert d['$extra']['topic']['title'] == 'test3'
    assert d['$extra']['topic']['$extra']['user']
    assert d['$extra']['topic']['$extra']['user']['id'] == 2

    assert len(d['$extra']['topic[]']) == 2


async def test_crud_read_2():
    db, session, MUsers, MTopics, MTopics2 = crud_db_init()

    c = SQLAlchemyCrud(None, {
        User: MUsers,
        Topic: MTopics,
    }, db)

    n0 = QueryInfo.from_json(Topic, {
        'id.eq': 1
    })
    n = n0.clone()

    ret = await c.get_list(n)
    assert len(ret) == 1


async def test_crud_read_3():
    db, session, MUsers, MTopics, MTopics2 = crud_db_init()
    c = SQLAlchemyCrud(None, {Topic: MTopics}, db)

    q = QueryInfo.from_json(Topic, {
        '$not': {
            'id.eq': 1
        }
    })

    ret = await c.get_list(q)

    v1 = {x.id for x in ret}
    v2 = {x.id for x in session.query(MTopics).where(MTopics.id != 1)}

    assert v1 == v2


async def test_crud_read_by_prefix():
    db, session, MUsers, MTopics, MTopics2 = crud_db_init()

    c = SQLAlchemyCrud(None, {
        User: MUsers
    }, db)

    n = QueryInfo.from_json(User, {
        'username.prefix': 'test4'
    })

    ret = await c.get_list(n)
    assert ret[0].to_dict()['username'] == 'test4'


async def test_crud_read_with_count():
    db, session, MUsers, MTopics, MTopics2 = crud_db_init()

    c = SQLAlchemyCrud(None, {
        Topic: MTopics,
    }, db)

    i = QueryInfo.from_json(Topic, {})
    i.limit = 1
    ret = await c.get_list(i, return_with_rows_count=True)
    assert len(ret) == 1
    assert ret.rows_count == session.query(MTopics).count()


async def test_crud_and_or():
    db, session, MUsers, MTopics, MTopics2 = crud_db_init()
    c = SQLAlchemyCrud(None, {User: MUsers}, db)

    info = QueryInfo.from_json(User, {
        '$or': {
            'id.in': [1, 2],
            '$and': {
                'id.ge': 4,
                'id.le': 5
            }
        }
    })

    ret = await c.get_list(info)
    assert [x.id for x in ret] == [1, 2, 4, 5]


async def test_crud_write_success():
    db, session, MUsers, MTopics, MTopics2 = crud_db_init()

    c = SQLAlchemyCrud(None, {
        User: MUsers,
        Topic: MTopics,
    }, db)

    v = ValuesToUpdate({
        'user_id': '444',
        'content': 'welcome'
    }, Topic).bind()

    ret = await c.update(QueryInfo(Topic, []), v)
    assert ret == [1, 2, 3, 4]

    for i in session.query(MTopics):
        assert i.content == 'welcome'


async def test_crud_insert_success():
    db, session, MUsers, MTopics, MTopics2 = crud_db_init()

    c = SQLAlchemyCrud(None, {
        User: MUsers,
        Topic: MTopics,
    }, db)

    v = ValuesToCreate({
        'title': 'test',
        'user_id': 1,
        'content': 'insert1',
        'time': 123
    }, Topic)
    v.bind()

    ret = await c.insert_many(Topic, [v])
    assert ret == [5]

    for i in session.query(MTopics).where(MTopics.id.in_(ret)):
        assert i.content == 'insert1'


async def test_crud_delete_success():
    db, session, MUsers, MTopics, MTopics2 = crud_db_init()

    c = SQLAlchemyCrud(None, {
        User: MUsers,
        Topic: MTopics,
    }, db)

    assert session.query(MTopics).where(MTopics.id == 1).count() == 1

    ret = await c.delete(QueryInfo.from_json(Topic, {
        'id.eq': 1
    }))

    assert len(ret) == 1
    assert session.query(MTopics).where(MTopics.id == 1).count() == 0

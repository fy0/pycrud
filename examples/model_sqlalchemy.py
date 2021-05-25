
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String, Sequence, Boolean


# ORM Initialize

engine = create_engine("sqlite:///:memory:")
Base = declarative_base()
Session = sessionmaker(bind=engine)


class UserModel(Base):
    __tablename__ = 'users'
    id = Column(Integer, Sequence('user_id_seq'), primary_key=True)
    nickname = Column(String)
    password = Column(String, default='password')
    is_admin = Column(Boolean, default=False)


class TopicModel(Base):
    __tablename__ = 'topics'
    id = Column(Integer, Sequence('topic_id_seq'), primary_key=True)
    title = Column(String)
    user_id = Column(Integer)
    content = Column(String, default='')


Base.metadata.create_all(engine)

session = Session()
session.add_all([
    UserModel(nickname='a', password='password1'),
    UserModel(nickname='b', password='password2'),
    UserModel(nickname='c', password='password3')
])

session.add_all([
    TopicModel(title='topic one', user_id=1),  # by user 1
    TopicModel(title='topic two', user_id=1),  # by user 1
    TopicModel(title='topic three', user_id=2),  # by user 2
])
session.commit()

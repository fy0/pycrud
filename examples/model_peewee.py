import peewee
from playhouse.db_url import connect


# ORM Initialize

db = connect("sqlite:///:memory:")


class UserModel(peewee.Model):
    nickname = peewee.TextField()
    password = peewee.TextField()
    is_admin = peewee.BooleanField(default=False)

    class Meta:
        table_name = 'users'
        database = db


class TopicModel(peewee.Model):
    title = peewee.TextField()
    user_id = peewee.IntegerField()
    content = peewee.TextField(default='')

    class Meta:
        table_name = 'topics'
        database = db


db.create_tables([UserModel, TopicModel])
UserModel(nickname='a', password='password1').save()
UserModel(nickname='b', password='password2').save()
UserModel(nickname='c', password='password3', is_admin=True).save()

TopicModel(title='topic one', user_id=1).save()  # by user1
TopicModel(title='topic two', user_id=1).save()  # by user1
TopicModel(title='topic three', user_id=2).save()  # by user2

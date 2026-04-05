from datetime import datetime

from peewee import CharField, DateTimeField

from app.database import BaseModel


class User(BaseModel):
    username = CharField()
    email = CharField()
    created_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        table_name = 'users'

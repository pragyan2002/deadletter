from datetime import datetime, timezone

from peewee import CharField, DateTimeField

from app.database import BaseModel


class User(BaseModel):
    username = CharField(unique=True)
    email = CharField(unique=True)
    created_at = DateTimeField(default=lambda: datetime.now(timezone.utc))

    class Meta:
        table_name = 'users'

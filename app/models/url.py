from datetime import datetime, timezone

from peewee import BooleanField, CharField, DateTimeField, ForeignKeyField, TextField

from app.database import BaseModel
from app.models.user import User


class Url(BaseModel):
    user = ForeignKeyField(User, backref='urls', column_name='user_id')
    short_code = CharField(max_length=6, unique=True)
    original_url = TextField()
    title = CharField()
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=lambda: datetime.now(timezone.utc))
    updated_at = DateTimeField(default=lambda: datetime.now(timezone.utc))

    class Meta:
        table_name = 'urls'

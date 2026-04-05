from datetime import datetime, timezone

from peewee import CharField, DateTimeField, ForeignKeyField
from playhouse.postgres_ext import BinaryJSONField

from app.database import BaseModel
from app.models.url import Url
from app.models.user import User


class Event(BaseModel):
    url = ForeignKeyField(Url, backref='events', column_name='url_id')
    user = ForeignKeyField(User, backref='events', column_name='user_id')
    event_type = CharField()  # 'created' | 'updated' | 'deleted'
    timestamp = DateTimeField(default=lambda: datetime.now(timezone.utc))
    details = BinaryJSONField()

    class Meta:
        table_name = 'events'

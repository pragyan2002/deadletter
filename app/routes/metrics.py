import time

import psutil
from flask import Blueprint, jsonify

from app.models.event import Event
from app.models.url import Url

metrics_bp = Blueprint('metrics', __name__)

_START_TIME = time.time()


@metrics_bp.route('/metrics')
def metrics():
    vm = psutil.virtual_memory()
    return jsonify(
        cpu_percent=psutil.cpu_percent(),
        memory_used_mb=vm.used // 1024 // 1024,
        memory_total_mb=vm.total // 1024 // 1024,
        uptime_seconds=int(time.time() - _START_TIME),
        urls_total=Url.select().count(),
        urls_active=Url.select().where(Url.is_active == True).count(),
        urls_inactive=Url.select().where(Url.is_active == False).count(),
        events_total=Event.select().count(),
    )

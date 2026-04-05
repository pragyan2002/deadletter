import logging
import os
import re
import threading
import time
from collections import deque

import apprise

from app.database import db

logger = logging.getLogger(__name__)

_DISCORD_HTTPS_RE = re.compile(
    r"https://discord(?:app)?\.com/api/webhooks/(?P<webhook_id>\d+)/(?P<token>[\w-]+)"
)


def _discord_https_to_apprise(url: str) -> str | None:
    m = _DISCORD_HTTPS_RE.match(url.strip())
    if not m:
        return None
    return f"discord://{m.group('webhook_id')}/{m.group('token')}"


_lock = threading.Lock()
_ERROR_WINDOW_SECONDS = 300
_HIGH_ERROR_THRESHOLD = 5
_error_window: deque[float] = deque()
_db_consecutive_failures: int = 0
_db_is_down: bool = False
_high_error_alerted: bool = False


def record_500_error() -> None:
    """Record a 500 error. Called from the Flask error handler. Always safe to call."""
    with _lock:
        _error_window.append(time.monotonic())


def start_alerting_thread(app) -> None:
    """Start the background alerting thread if DISCORD_WEBHOOK_URL is configured."""
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if not webhook_url or "..." in webhook_url:
        logger.info("alerting: DISCORD_WEBHOOK_URL not configured - alerting disabled")
        return
    apprise_url = _discord_https_to_apprise(webhook_url)
    if apprise_url is None:
        logger.warning("alerting: DISCORD_WEBHOOK_URL format unrecognised - alerting disabled")
        return
    t = threading.Thread(
        target=_alert_loop,
        args=(app, apprise_url),
        name="alerting-thread",
        daemon=True,
    )
    t.start()
    logger.info("alerting: background thread started")


def _send_alert(apprise_url: str, title: str, body: str) -> None:
    try:
        ap = apprise.Apprise()
        ap.add(apprise_url)
        ap.notify(title=title, body=body)
    except Exception:
        logger.exception("alerting: failed to send alert '%s'", title)


def _check_db(app, apprise_url: str) -> None:
    global _db_consecutive_failures, _db_is_down
    success = False
    try:
        with app.app_context():
            db.connect(reuse_if_open=True)
            db.execute_sql("SELECT 1")
            db.close()
        success = True
    except Exception:
        logger.exception("alerting: DB connectivity check failed")

    should_send_down = False
    should_send_recovery = False
    failures_count = 0
    with _lock:
        if success:
            if _db_is_down:
                _db_is_down = False
                _db_consecutive_failures = 0
                should_send_recovery = True
            else:
                _db_consecutive_failures = 0
        else:
            _db_consecutive_failures += 1
            failures_count = _db_consecutive_failures
            if _db_consecutive_failures >= 2 and not _db_is_down:
                _db_is_down = True
                should_send_down = True

    if should_send_down:
        _send_alert(
            apprise_url,
            title="Service Down",
            body=f"deadletter: DB check failed {failures_count} consecutive times. Service may be degraded.",
        )
    elif should_send_recovery:
        _send_alert(
            apprise_url,
            title="Service Recovered",
            body="deadletter: database connectivity restored.",
        )


def _check_error_rate(apprise_url: str) -> None:
    global _high_error_alerted
    now = time.monotonic()
    cutoff = now - _ERROR_WINDOW_SECONDS
    should_alert = False
    count = 0
    with _lock:
        while _error_window and _error_window[0] < cutoff:
            _error_window.popleft()
        count = len(_error_window)
        if count >= _HIGH_ERROR_THRESHOLD and not _high_error_alerted:
            _high_error_alerted = True
            should_alert = True
        elif count < _HIGH_ERROR_THRESHOLD and _high_error_alerted:
            _high_error_alerted = False
    if should_alert:
        _send_alert(
            apprise_url,
            title="High Error Rate",
            body=f"deadletter: {count} HTTP 500 errors in the last 5 minutes.",
        )


def _alert_loop(app, apprise_url: str) -> None:
    CHECK_INTERVAL = 60
    while True:
        try:
            _check_db(app, apprise_url)
        except Exception:
            logger.exception("alerting: unhandled error in _check_db")
        try:
            _check_error_rate(apprise_url)
        except Exception:
            logger.exception("alerting: unhandled error in _check_error_rate")
        time.sleep(CHECK_INTERVAL)

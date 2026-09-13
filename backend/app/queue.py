"""RQ queue connection + enqueue helper.

Shared by the API (producer — routers enqueue jobs here) and the worker
(consumer — see workers/run.py, which listens on the same QUEUE_NAME). Both
sides must agree on the queue name and Redis connection; importing it from
one place avoids drift between them.
"""

from redis import Redis
from rq import Queue

from app.config import settings

QUEUE_NAME = "styleloop"


def get_queue() -> Queue:
    return Queue(QUEUE_NAME, connection=Redis.from_url(settings.REDIS_URL))

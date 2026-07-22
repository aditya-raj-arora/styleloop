"""Worker entrypoint.

Starts an RQ worker whose Redis connection comes from application settings — i.e.
a real environment variable read in Python — instead of depending on shell
variable expansion in a platform "start command" (which some platforms, Railway
included, do not perform, passing `$REDIS_URL` through literally). Run with:

    python -m app.workers.run
"""

from urllib.parse import urlparse

from redis import Redis
from rq import Worker

from app.config import settings

QUEUE_NAME = "styleloop"

_VALID_SCHEMES = {"redis", "rediss", "unix"}


def main() -> None:
    url = settings.REDIS_URL
    scheme = urlparse(url).scheme
    if scheme not in _VALID_SCHEMES:
        raise SystemExit(
            f"REDIS_URL is not a valid Redis URL (got {url!r}). "
            "Set REDIS_URL to a redis:// / rediss:// / unix:// URL. On Railway, add "
            "it on this service as a reference to the Redis service's REDIS_URL."
        )

    connection = Redis.from_url(url)
    worker = Worker([QUEUE_NAME], connection=connection)
    worker.work()


if __name__ == "__main__":
    main()

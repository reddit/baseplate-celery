import logging

from baseplate import Baseplate
from baseplate.clients.sqlalchemy import SQLAlchemySession
from baseplate.lib import config
from baseplate.lib.secrets import secrets_store_from_config
from celery import Celery
from celery import Task
from celery.worker.request import Request
from psycogreen.gevent import patch_psycopg

logger = logging.getLogger(__name__)


def parse_celery_configs(app_config: config.RawConfig, prefix: str = "celery."):
    """Make a BaseplateCelery application from a configuration dictionary.

    The keys useful to :py:func:`celery_from_config` should be prefixed, e.g.
    ``celery.service_name``, ``celery.broker_url``, etc. The ``prefix`` argument
    specifies the prefix used to filter keys.

    Supported keys:

    * ``service_name``          (required): the name of service.
    * ``broker_url``            (required): a Redis URL like ``redis://localhost/0``.
    * ``db.url``                (optional): Postgres configs for backend database.
    * ``db.credentials_secret`` (optional): the key used to retrieve the database credentials from ``secrets``

    """
    assert prefix.endswith(".")
    parser = config.SpecParser(
        {
            "service_name": config.String,
            "broker_url": config.String,
            "db": config.DictOf(config.String),
        }
    )
    options = parser.parse(prefix[:-1], app_config)
    return options


def short_task_name(task_name: str) -> str:
    return task_name.split(".")[-1]


def emit_celery_metric(context, task_name, **tags):
    tags = {"task_name": short_task_name(task_name), **tags}
    context.metrics.counter("celery_task", tags=tags).increment()
    context.metrics.flush()


class BaseplateRequest(Request):
    def on_timeout(self, soft, timeout):
        super().on_timeout(soft, timeout)
        emit_celery_metric(
            self.task._context, self.task.name, success=False, timeout=True
        )
        self._context.sentry.capture_message(
            "Task {self.task.name} timed out after {timeout} seconds"
        )


class BaseplateTask(Task):
    Request = BaseplateRequest
    acks_late = True
    track_started = True

    _context = None

    def __call__(self, *args, **kwargs):
        baseplate = self._app._baseplate
        self._context = baseplate.make_context_object()
        with baseplate.make_server_span(
            self._context, f"celery.{short_task_name(self.name)}"
        ):
            return super().__call__(*args, **kwargs)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        emit_celery_metric(self._context, self.name, success=False)
        return super().on_failure(exc, task_id, args, kwargs, einfo)

    def on_success(self, retval, task_id, args, kwargs):
        emit_celery_metric(self._context, self.name, success=True)
        return super().on_success(retval, task_id, args, kwargs)


class BaseplateCelery(Celery):
    def __init__(self, *args, **kwargs):
        self._app_config = None
        self._baseplate = None

        super().__init__(*args, **kwargs)

    def set_baseplate(self, baseplate: Baseplate):
        self._baseplate = baseplate
        self._app_config = parse_celery_configs(baseplate._app_config)

        secrets = secrets_store_from_config(baseplate._app_config, timeout=60)
        session_factory = SQLAlchemySession(secrets).parse("", self._app_config.db)
        backend_url = f"db+{session_factory.engine.url}"

        self.conf.update(
            broker_url=self._app_config.broker_url, result_backend=backend_url
        )

    def run_workers(self, app_config: config.RawConfig):
        """ Starts the worker, sets up context for future use in workers """
        # we use gevent pool so lets patch psycopg2 so it doesnt block
        patch_psycopg()

        cfg = config.parse_config(
            app_config,
            {
                "command": config.Optional(config.String, default=None),
                "tasks": config.String,
            },
        )

        worker_command = ["worker"]

        if cfg.command:
            worker_command_flags = cfg.command.split(" ")
            worker_command.extend(worker_command_flags)

        # Register tasks
        self.autodiscover_tasks([cfg.tasks])

        logger.info("Starting celery workers")
        self.start(worker_command)

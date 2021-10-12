import logging

from baseplate import Baseplate
from baseplate.lib import config
from celery import Celery
from celery import Task

logger = logging.getLogger(__name__)


def parse_celery_configs(
    app_config: config.RawConfig, prefix: str = "celery."
) -> config.ConfigNamespace:
    """Make a BaseplateCelery application from a configuration dictionary.

    The keys useful to :py:func:`celery_from_config` should be prefixed, e.g.
    ``celery.service_name``, ``celery.broker_url``, etc. The ``prefix`` argument
    specifies the prefix used to filter keys.

    Supported keys:

    * ``service_name``          (required): the name of service.
    * ``broker_url``            (required): a Redis URL like ``redis://localhost/0``.

    """
    assert prefix.endswith(".")
    parser = config.SpecParser(
        {"service_name": config.String, "broker_url": config.String}
    )
    options = parser.parse(prefix[:-1], app_config)
    return options


def short_task_name(task_name: str) -> str:
    return task_name.split(".")[-1]


def emit_celery_metric(context, task_name, **tags):
    tags = {"task_name": short_task_name(task_name), **tags}
    context.metrics.counter("celery_task", tags=tags).increment()
    context.metrics.flush()


class BaseplateTask(Task):
    # this lets us get away with injecting the context task arg
    typing = False

    def __call__(self, *args, **kwargs):
        baseplate = self._app._baseplate
        context = baseplate.make_context_object()
        with baseplate.make_server_span(
            context, f"celery.{short_task_name(self.name)}"
        ):
            try:
                ret = super().__call__(context, *args, **kwargs)
            except Exception:
                emit_celery_metric(context, self.name, success=False)
                raise
            else:
                emit_celery_metric(context, self.name, success=True)

        return ret


class BaseplateCelery(Celery):
    def __init__(self, *args, **kwargs):
        self._app_config = None
        self._baseplate = None

        super().__init__(*args, **kwargs)
        self.Task = BaseplateTask

    def set_baseplate(self, baseplate: Baseplate):
        self._baseplate = baseplate
        self._app_config = parse_celery_configs(baseplate._app_config)
        self.conf.update(broker_url=self._app_config.broker_url)

    def run_workers(self, app_config: config.RawConfig):
        """ Starts the worker, sets up context for future use in workers """
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

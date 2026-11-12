"""Celery integration for baseplate.py services."""

import logging
from typing import cast

from baseplate import Baseplate
from baseplate.lib import config
from celery import Celery, Task

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
    assert prefix.endswith(".")  # noqa: S101 - matches baseplate's *_from_config helpers
    parser = config.SpecParser({"service_name": config.String, "broker_url": config.String})
    return parser.parse(prefix[:-1], app_config)


def short_task_name(task_name: str) -> str:
    """Return the last dotted component of a task name."""
    return task_name.rsplit(".", maxsplit=1)[-1]


def emit_celery_metric(context, task_name, **tags):
    """Increment and flush the ``celery_task`` counter for a task."""
    tags = {"task_name": short_task_name(task_name), **tags}
    context.metrics.counter("celery_task", tags=tags).increment()
    context.metrics.flush()


class BaseplateTask(Task):
    """Celery task that runs in a baseplate server span, with a ``RequestContext`` first arg."""

    # this lets us get away with injecting the context task arg
    typing = False

    def __call__(self, *args, **kwargs):
        """Run the task in a server span, passing a new ``RequestContext`` as the first argument."""
        # set_baseplate() runs before workers start, so _baseplate is set by the time tasks run.
        baseplate = cast("Baseplate", cast("BaseplateCelery", self._app)._baseplate)
        name = cast("str", self.name)
        context = baseplate.make_context_object()
        with baseplate.make_server_span(context, f"celery.{short_task_name(name)}"):
            try:
                ret = super().__call__(context, *args, **kwargs)
            except Exception:
                emit_celery_metric(context, self.name, success=False)
                raise
            else:
                emit_celery_metric(context, self.name, success=True)

        return ret


class BaseplateCelery(Celery):
    """Celery application whose tasks run with baseplate context and telemetry."""

    def __init__(self, *args, **kwargs):
        self._app_config = None
        self._baseplate = None

        super().__init__(*args, **kwargs)
        self.Task = BaseplateTask

    def set_baseplate(self, baseplate: Baseplate):
        """Attach ``baseplate`` and configure the broker from its ``celery.*`` settings."""
        self._baseplate = baseplate
        self._app_config = parse_celery_configs(baseplate._app_config)
        self.conf.update(broker_url=self._app_config.broker_url)

    def run_workers(self, app_config: config.RawConfig):
        """Start the worker, setting up context for future use in workers."""
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

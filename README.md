# baseplate-celery

[![Reticle Badge](https://reticle.snooguts.net/api/reticle_badge?repo_name=reddit/baseplate-celery)](https://reticle.snooguts.net/repos/reddit/baseplate-celery)
[![AI Readiness](https://reticle.snooguts.net/api/category_badge?repo_name=reddit%2Fbaseplate-celery&category_name=AI%20Readiness)](https://reticle.snooguts.net/repos/reddit/baseplate-celery)
[![Build Status](https://drone.build.ue1.snooguts.net/api/badges/reddit/baseplate-celery/status.svg?ref=refs/heads/main)](https://drone.build.ue1.snooguts.net/reddit/baseplate-celery)

Baseplate Celery allows us to integrate Celery in Baseplate.py services. [Celery](https://docs.celeryproject.org/en/stable/getting-started/introduction.html) is an open source asynchronous task queue. Integrating your Baseplate.py service with Celery can enable you to offload some tasks to run in the background, while leveraging some of Baseplate.py's configurations and telemetry.

Baseplate Celery will allow you to:
1. Instantiate an instance of Celery.
2. Identify background task functions within your application with a simple decorator.
3. Push background tasks to a message queue (or broker), currently supported broker is Redis. 
4. Instantiate Celery workers to pick up tasks from the queue and execute in the background.


## Usage

Install the library:

```console
$ pip install baseplate-celery
```

### 1. Instantiate BaseplateCelery
Configure `BaseplateCelery` from the main application's configuration file. 

```ini
[app:main]

...

# required: name of application
celery.service_name = helloworld

# required: the Redis instance to connect to as the message broker
celery.broker_url = redis://localhost:6379/1

...

```

It is recommended to create a dedicated module for `BaseplateCelery` in your application. For example, your project structure could look like:
```
helloworld/jobs/__init__.py
               /celery.py
               /tasks.py
```

Create the `BaseplateCelery` instance. To use `BaseplateCelery` within your application, import this instance.
#### `helloworld/jobs/celery.py`
```python
from baseplate-celery import BaseplateCelery

celery_app = BaseplateCelery("helloworld")
```

### 2. Identify background tasks
Create a file called `tasks.py` in this module which contains all the functions you would like to register as Celery tasks. One option is to define all tasks directly in this file. Another option if the tasks are defined in various parts of your application is to import all of them into the `tasks.py` file.

#### `helloworld/jobs/tasks.py`
```python
from .celery import celery_app


@celery_app.task
def add(ctx, x, y):
    return x + y
```

All task functions pass the Baseplate `RequestContext` as a parameter to avoid issues of concurrency.

### 3. Configure BaseplateCelery workers
In your application's configuration `.ini` file, add a section for configuring the `celery-worker`.

```ini
[app:celery-worker]

# required: factory specifies the entry point for setting up Baseplate on the Celery worker
factory = helloworld:make_celery_worker

# required: the module which contains the `tasks.py` file
tasks = helloworld.jobs

# optional: additional command line arguments for starting the Celery worker
command = --loglevel INFO --pool gevent --time-limit 180 --concurrency 1
```

To start the celery worker, use the [`baseplate-serve`](https://baseplate.readthedocs.io/en/stable/cli/serve.html) command:
```
baseplate-serve example.ini --app-name celery-worker
```

Your application might already have a `make_baseplate` function doing all the Baseplate setup. The celery worker's entrypoint function should do the exact same Baseplate setup and then start the workers. For example:

```py
def make_baseplate(app_config):
    baseplate = Baseplate(app_config)
    baseplate.configure_observers()
    celery_app.set_baseplate(baseplate)
    ...


def make_celery_worker(app_config):
    make_baseplate(app_config)
    celery_app.run_workers(app_config)
```


### 4. Push background tasks to broker
Now that your application is set configured with a BaseplateCelery instance and the Celery workers are running, you can push a task to the broker by calling:
```
add.delay(4, 4)
```

## Documentation: 

See [the documentation] for more information.

[the documentation]: 

## Development

Requires [uv](https://docs.astral.sh/uv/) and [lefthook](https://lefthook.dev/). With
[direnv](https://direnv.net/), `direnv allow` runs `make scaffold` and activates `.venv` whenever you
enter the repo; otherwise run it yourself:

```console
$ make scaffold
```

[Zed](https://zed.dev/) project settings (`.zed/`) use ty and ruff as the Python language servers.

The following make targets are provided:

* `scaffold`: Create the virtualenv with the dev dependencies and install git hooks.
* `fmt`: Apply automatic formatting and lint fixes.
* `lint`: Run ruff and ty.
* `test`: Run the test suite.
* `test-cov`: Run the test suite with coverage.
* `build`: Build the sdist and wheel into `dist/`.
* `generate`: Regenerate the [Infrared v2](infrared/) configs (Makefile, `.gitignore`, `REDDITOWNERS`, Renovate, `.reddit/`). Requires Go and access to `github.snooguts.net`.

## Publishing

Drone ([`infrared/legacydrone.yaml`](infrared/legacydrone.yaml)) lints and tests every pull request
on Python 3.11-3.15, plus at the lowest and highest dependency versions allowed by
`pyproject.toml` (`UV_RESOLUTION=lowest-direct` and `uv lock --upgrade`), and publishes to
Artifactory:

* `v*` tags publish `<tag>` to `reddit-python-prod`.
* Pushes to `main` publish `<latest-tag>+git.<sha>` snapshots to `reddit-python-dev`.

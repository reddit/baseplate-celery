# baseplate-celery.py

Baseplate Celery allows us to integrate Celery in Baseplate.py services. [Celery](https://docs.celeryproject.org/en/stable/getting-started/introduction.html) is an open source asynchronous task queue. Integrating your Baseplate.py service with Celery can enable you to offload some tasks to run in the background, while leveraging some of Baseplate.py's configurations and telemetry.

Baseplate Celery will allow you to:
1. Instantiate an instance of Celery.
2. Identify background task functions within your application with a simple decorator.
3. Push background tasks to a message queue, currently Redis. 
4. Instantiate Celery workers to pick up tasks from the queue and execute in the background.


## Usage

Install the library:

```console
$ pip install baseplate-celery
```

### Instantiate an instance of BaseplateCelery
Firstly, we can configure `BaseplateCelery` from the main application's config file. 
- `celery.service_name`: [required] Name of main application.
- `celery.broker_url`: [required] Celery requires a broker to act as the message queue for transporting tasks. Baseplate Celery is currently configured to enable Redis as the chosen broker.
- `celery.db.url`: [optional] URL of the results backend database, used for storing the states of tasks.
- `celery.db.credentials_secret`: [optional] The key used to retrieve the database credentials

Example:
```ini
[app:main]
celery.service_name = helloworld
celery.broker_url = redis://localhost:6379/1
celery.db.url = sqlite:///
```

It is recommended to create a dedicated module for `BaseplateCelery` in your application. For example, your project structure could look like:
```
helloworld/jobs/__init__.py
               /celery.py
               /tasks.py
```

Create the `BaseplateCelery` instance. To use `BaseplateCelery` within your application, import this instance.
helloworld/jobs/celery.py
```python
from baseplate-celery import BaseplateCelery
celery_app = BaseplateCelery("helloworld")
```

### Identify background tasks
Create a file called `tasks.py` in this module which contains all the functions you would like to register as Celery tasks. One option is to define all tasks directly in this file. Another option if the tasks are defined in various parts of your application is to import all of them in the `tasks.py` file.
helloworld/jobs/tasks.py
```python
from .celery import celery_app

@celery_app.task
def add(x, y):
    return x + y
```


### Configure BaseplateCelery workers
In your .ini file, add a section for configuring the `celery-worker`.
- `factory`: [required] The factory function, which is the entry point for setting up Baseplate on the Celery worker.
- `tasks`: [required] The module which contains the `tasks.py` file.
- `command`: [optional] Additional command line arguments for starting the Celery worker.

```ini
[app:celery-worker]
factory = helloworld:make_celery_worker
tasks = helloworld.jobs
command = --loglevel INFO --pool gevent --time-limit 180 --concurrency 1
```

Start the celery worker:
```baseplate-serve example.ini --app-name celery-worker```


### Push background tasks to broker
```add.delay(4, 4)```

Documentation: 

See [the documentation] for more information.

[the documentation]: 

## Development

A Dockerfile is provided to get a development environment running. To use it,
build the base Docker image:

```console
$ docker build -t baseplate_celery .
```

And then fire up the environment and use the provided Makefile targets to do
common tasks:

```console
$ docker run -it -v $PWD:/src -w /src baseplate_celery
$ make fmt
```

The following make targets are provided:

* `fmt`: Apply automatic formatting to the source code.
* `lint`: Run linters on the code.
* `test`: Run the test suite.
* `docs`: Build the docs. Output can be found in `build/html/`.

Note: some tests are skipped by default locally because they are quite slow.
Enable these by setting CI=true in the environment: `CI=true make test`.

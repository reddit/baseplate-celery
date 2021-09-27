# baseplate-celery.py

Experiments allow us to determine the impact of changes we make. This library
helps you run and track them in Baseplate.py services.

Documentation: 

## Usage

Install the library:

```console
$ pip install baseplate-celery
```

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

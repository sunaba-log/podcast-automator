# Targets for setup / cleanup
.PHONY: all
.PHONY: install  # install dependencies including development
.PHONY: lock  # re-lock dependendencies without updating them
.PHONY: upgrade  # upgrade uv and dependencies
.PHONY: lint  # executes various style and static code analysis tools
.PHONY: format  # format the code
.PHONY: fix  # format the code and apply safe fixes discovered by static code analysis tools
.PHONY: test  # executes pytest
.PHONY: clean  # clean tool artifacts and virtualenv
.PHONY: docker-build  # build a docker image. use DOCKER_TAG=:customtag to change tag from latest
.PHONY: jupyter  # launch Jupyter Lab

-include .env

SHELL := /bin/bash
TEST_FOLDER := tests
IMAGE_NAME ?= podcast-automator-app
DOCKER_TAG ?= :latest

all: install fix lint test

install:
	uv sync

lock:
	uv lock

upgrade:
	uv lock --upgrade
	uv sync

lint:
	@echo "- Lint -"
	uv run ruff check .
	@echo "- Lint Format -"
	uv run ruff format --check .
	@echo "- Lint Project -"
	uv pip check

format:
	uv run ruff format .

fix:
	$(MAKE) format
	uv run ruff check --fix .

test:
	uv run pytest --cov=. $(TEST_FOLDER)

clean:
	uv run ruff clean || true
	find . -type f -name '*.py[co]' -delete -o -type d -name __pycache__ -delete
	rm -rf .pytest* .ruff* .coverage dist .venv

docker-build:
	cd .. && DOCKER_BUILDKIT=1 docker build -f app/Dockerfile . -t $(IMAGE_NAME)$(DOCKER_TAG)

jupyter:
	uv run jupyter lab

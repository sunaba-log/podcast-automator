# Targets for setup / cleanup
.PHONY: install  # install dependencies including development
.PHONY: clean  # clean tool artifacts and virtualenv
# Targets for verification
.PHONY: lint  # executes various style and static code analysis tools
.PHONY: test  # executes pytest
# Targets for code formatting / code fixing
.PHONY: format  # format the code
.PHONY: fix  # format the code and apply safe fixes discovered by static code analysis tools
# Execute install fix lint test
.PHONY: all
# Docker related targets
.PHONY: docker-build  # build a docker image. use DOCKER_TAG=:customtag to change tag from latest
# Dependency management
.PHONY: upgrade  # upgrade uv and dependencies
# Dev tooling
.PHONY: jupyter  # launch Jupyter Lab

-include .env

SHELL := /bin/bash
TEST_FOLDER := tests

install:
	uv sync

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

jupyter:jupyter:
	$(MAKE) install
	poetry run jupyter notebook
	uv run jupyter lab

clean:
	uv run ruff clean || true
	find . -type f -name '*.py[co]' -delete -o -type d -name __pycache__ -delete
	rm -rf .pytest* .ruff* .coverage dist .venv

all: install fix lint test

docker-build:
	cd .. && DOCKER_BUILDKIT=1 docker build -f app/Dockerfile . -t podcast-automator${DOCKER_TAG}

.PHONY: install  # install dependencies including development
.PHONY: clean  # clean tool artifacts and virtualenv
.PHONY: lint  # executes various style and static code analysis tools
.PHONY: test  # executs pytest
.PHONY: format  # format the code
.PHONY: fix  # format the code and apply save fixes discovered by static code analysis tools
.PHONY: lock  # re-lock dependendencies without updating them
.PHONY: upgrade  # upgrade uv and dependencies

install:
	uv sync --no-install-project

lock:
	uv lock

upgrade:
	uv lock --upgrade
	uv sync --no-install-project

format:
	uv run ruff format .

fix:
	$(MAKE) format
	uv run ruff check --fix .

lint:
	uv run ruff check .

test:
	uv run pytest

clean:
	rm -rf .venv .ruff_cache .pytest_cache
	find . -type d -name '__pycache__' -exec rm -rf {} +

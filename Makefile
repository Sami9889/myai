PYTHON ?= python3

.PHONY: lint install clean
install:
\t./install.sh

lint:
\t$(PYTHON) -m compileall -q core_engine agent_runtime tools cli_interface utils

clean:
\trm -rf .venv build dist *.egg-info __pycache__ core_engine/__pycache__ agent_runtime/__pycache__ tools/__pycache__ cli_interface/__pycache__ utils/__pycache__

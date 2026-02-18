SHELL := /bin/bash

PYTHON ?= python3
PYTHONPATH_LOCAL := $(CURDIR)/src/lib

.PHONY: help ut sy test ci

help:
	@echo "test targets:"
	@echo "  make ut    - run unit tests"
	@echo "  make sy    - run system tests"
	@echo "  make test  - run ut then sy"

ut:
	@echo "Running unit tests (ut)..."
	@FORCE_COLOR=1 PYTHONPATH="$(PYTHONPATH_LOCAL)" $(PYTHON) src/tst/ut/run_ut.py

sy:
	@echo "Running system tests (sy)..."
	@FORCE_COLOR=1 PYTHONPATH="$(PYTHONPATH_LOCAL)" $(PYTHON) src/tst/sy/run_sy.py

test: ut sy

ci: test

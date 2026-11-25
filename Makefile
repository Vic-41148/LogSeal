PY ?= python3
NAME ?= $(USER)
VENV_BIN := $(if $(wildcard .venv/Scripts),.venv/Scripts,.venv/bin)

.PHONY: help setup check test selftest lint ci stack demo down status reset bench dataset train eval clean

help:
	@echo "make setup     create .venv and install everything"
	@echo "make check     fast contract check"
	@echo "make test      full test suite (stdlib unittest)"
	@echo "make selftest  20-check core mutation selftest"
	@echo "make ci        check + test + selftest + lint"
	@echo "make stack     private vaults on ports for your name"
	@echo "make demo      private vaults + generator + console"
	@echo "make down      stop your stack"
	@echo "make status    show your stack"
	@echo "make reset     clear your stack data"
	@echo "make bench     write bench.json"
	@echo "make dataset   write dataset/ for ml.py"
	@echo "make train     train the burst model"
	@echo "make eval      write metrics.json"

setup:
	$(PY) -m venv .venv
	$(VENV_BIN)/python -m pip install --upgrade pip
	$(VENV_BIN)/python -m pip install -r requirements.txt -r requirements-dev.txt

check:
	$(PY) scripts/check_contract.py

test:
	$(PY) -m unittest discover -s tests -t . -v

selftest:
	$(PY) seal.py --selftest

lint:
	$(VENV_BIN)/ruff check .

ci: check test selftest lint

stack:
	$(PY) scripts/local_stack.py up --name $(NAME)

demo:
	$(PY) scripts/local_stack.py up --name $(NAME) --with-gen --with-console

down:
	$(PY) scripts/local_stack.py down --name $(NAME)

status:
	$(PY) scripts/local_stack.py status --name $(NAME)

reset:
	$(PY) scripts/local_stack.py reset --name $(NAME)

bench:
	$(PY) bench.py

dataset:
	$(PY) gen.py --dataset dataset

train:
	$(PY) ml.py train

eval:
	$(PY) ml.py eval

clean:
	rm -rf .run __pycache__ tests/__pycache__ .ruff_cache

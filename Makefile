PYTHON ?= python3
PYTHON_BOOTSTRAP ?= python3
PIP ?= $(PYTHON) -m pip
APP_MODULE ?= vision_mouse.main
PYTHONPATH := src
PYCACHE_DIR := $(CURDIR)/.build/pycache
VENV_PYTHON := $(CURDIR)/.venv/bin/python

ifneq ($(wildcard $(VENV_PYTHON)),)
PYTHON := $(VENV_PYTHON)
PIP := $(PYTHON) -m pip
endif

.PHONY: help venv check-python install dev-install run test build package clean

help:
	@echo "Comandos disponíveis:"
	@echo "  make venv         - cria .venv usando PYTHON_BOOTSTRAP"
	@echo "  make install      - instala as dependências do projeto"
	@echo "  make dev-install  - instala o projeto em modo editável"
	@echo "  make run          - executa a aplicação"
	@echo "  make test         - roda a suíte de testes"
	@echo "  make build        - valida o código compilando os módulos Python"
	@echo "  make package      - gera sdist/wheel da aplicação"
	@echo "  make clean        - remove artefatos de build e cache"

venv:
	$(PYTHON_BOOTSTRAP) -m venv .venv
	@echo "Virtualenv criada em .venv"
	@echo "Instale dependências com: make install"

check-python:
	@$(PYTHON) -c "import sys; base = getattr(sys, '_base_executable', sys.executable); xcode = '/Applications/Xcode.app/Contents/Developer' in base; sys.exit('Unsupported Python runtime for this MVP: ' + base + '. Create a virtualenv from a non-Xcode interpreter, for example make venv PYTHON_BOOTSTRAP=/path/to/python3.11, then run make install.') if xcode else None"

install: check-python
	$(PIP) install .

dev-install: check-python
	$(PIP) install -e .

run: check-python
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m $(APP_MODULE)

test: check-python
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m unittest discover -s tests -v

build: check-python
	@mkdir -p $(PYCACHE_DIR)
	PYTHONPATH=$(PYTHONPATH) PYTHONPYCACHEPREFIX=$(PYCACHE_DIR) $(PYTHON) -m compileall src tests

package: check-python
	$(PYTHON) -m build

clean:
	rm -rf .build dist *.egg-info

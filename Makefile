ENV_DIR := $(shell pwd)/_env
ENV_PYTHON := ${ENV_DIR}/bin/python
PYTHON_BIN := $(shell which python)

DEB_COMPONENT := crest
DEB_MAJOR_VERSION := 1.0${DEB_VERSION_QUALIFIER}
DEB_NAMES := crest homer homestead-prov

MAX_LINE_LENGTH ?= 99

# As we plan to deploy on 64 bit systems, by default target 64 bit. Disable this to attempt to build on 32 bit
# Note we do not plan to support 32 bit going forward, so this may be removed in the future
X86_64_ONLY=1

.DEFAULT_GOAL = all

.PHONY: all
all: help

.PHONY: help
help:
	@cat docs/development.md

.PHONY: test
test: setup_crest.py setup_homer.py setup_homestead_prov.py env
	PYTHONPATH=src:common ${ENV_DIR}/bin/python setup_crest.py test -v
	PYTHONPATH=src:common ${ENV_DIR}/bin/python setup_homer.py test -v
	PYTHONPATH=src:common ${ENV_DIR}/bin/python setup_homestead_prov.py test -v

${ENV_DIR}/bin/flake8: env
	${ENV_DIR}/bin/pip install flake8

${ENV_DIR}/bin/coverage: env
	${ENV_DIR}/bin/pip install coverage

verify: ${ENV_DIR}/bin/flake8
	${ENV_DIR}/bin/flake8 --select=E10,E11,E9,F src/

style: ${ENV_DIR}/bin/flake8
	${ENV_DIR}/bin/flake8 --select=E,W,C,N --max-line-length=100 src/

explain-style: ${ENV_DIR}/bin/flake8
	${ENV_DIR}/bin/flake8 --select=E,W,C,N --show-pep8 --first --max-line-length=100 src/

.PHONY: coverage
coverage: ${ENV_DIR}/bin/coverage setup_crest.py setup_homer.py setup_homestead_prov.py
	rm -rf htmlcov/
	${ENV_DIR}/bin/coverage erase
	${ENV_DIR}/bin/coverage run --append --source src --omit "**/test/**"  setup_crest.py test
	${ENV_DIR}/bin/coverage run --append --source src --omit "**/test/**"  setup_homer.py test
	${ENV_DIR}/bin/coverage run --append --source src --omit "**/test/**"  setup_homestead_prov.py test
	${ENV_DIR}/bin/coverage report -m
	${ENV_DIR}/bin/coverage html

.PHONY: env
env: ${ENV_DIR}/.eggs_installed

$(ENV_DIR)/bin/python: setup_crest.py setup_homer.py setup_homestead_prov.py common/setup.py
	# Set up a fresh virtual environment
	virtualenv --setuptools --python=$(PYTHON_BIN) $(ENV_DIR)
	$(ENV_DIR)/bin/easy_install -U "setuptools>=3.3"
	$(ENV_DIR)/bin/easy_install distribute

${ENV_DIR}/.eggs_installed : $(ENV_DIR)/bin/python $(shell find src/metaswitch -type f -not -name "*.pyc") $(shell find common/metaswitch -type f -not -name "*.pyc")
	# Generate .egg files for crest, homer, homestead_prov
	${ENV_DIR}/bin/python setup_crest.py bdist_egg -d .crest-eggs
	${ENV_DIR}/bin/python setup_homer.py bdist_egg -d .homer-eggs
	${ENV_DIR}/bin/python setup_homestead_prov.py bdist_egg -d .homestead_prov-eggs

	# Generate the egg files for internal crest dependencies
	cd common && EGG_DIR=../.crest-eggs make build_common_egg
	cd telephus && python setup.py bdist_egg -d ../.crest-eggs

	# Download the egg files crest depends upon
	${ENV_DIR}/bin/easy_install -zmaxd .crest-eggs/ .crest-eggs/*.egg

	# Install the downloaded egg files (this should match the postinst)
	${ENV_DIR}/bin/easy_install --allow-hosts=None -f .crest-eggs/ .crest-eggs/*.egg

	# Download the additional egg files homer depends upon
	${ENV_DIR}/bin/easy_install -zmxd .homer-eggs/ .homer-eggs/*.egg

	# Install the downloaded egg files (this should match the postinst)
	${ENV_DIR}/bin/easy_install --allow-hosts=None -f .homer-eggs/ .homer-eggs/*.egg

	# Download the additional egg files homestead_prov depends upon
	${ENV_DIR}/bin/easy_install -zmxd .homestead_prov-eggs/ .homestead_prov-eggs/*.egg

	# Install the downloaded egg files (this should match the postinst)
	${ENV_DIR}/bin/easy_install --allow-hosts=None -f .homestead_prov-eggs/ .homestead_prov-eggs/*.egg

	# Touch the sentinel file
	touch $@

include build-infra/cw-deb.mk

.PHONY: deb
deb: env deb-only

.PHONY: clean
clean: envclean pyclean

.PHONY: pyclean
pyclean:
	-find src -name \*.pyc -exec rm {} \;
	-rm -r src/*.egg-info
	-rm .coverage
	-rm -r htmlcov/

.PHONY: envclean
envclean:
	-rm -r .crest-eggs .homer-eggs .homestead_prov-eggs build-crest build-homer build-homestead_prov ${ENV_DIR}

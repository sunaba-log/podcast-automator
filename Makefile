.PHONY: all
.PHONY: install  # install dependencies including development
.PHONY: lock  # re-lock dependendencies without updating them
.PHONY: upgrade  # upgrade uv and dependencies
.PHONY: lint  # executes various style and static code analysis tools
.PHONY: format  # format the code
.PHONY: fix  # format the code and apply save fixes discovered by static code analysis tools
.PHONY: test  # executs pytest
.PHONY: clean  # clean tool artifacts and virtualenv
.PHONY: docker-build  # build a docker image.
.PHONY: terraform-docker-build  # build infrastructure docker image
.PHONY: terraform-upgrade # initializes terraform with the latest versions
.PHONY: terraform-fix  # fix terraform code
.PHONY: terraform-validate  # validate terraform code
.PHONY: terraform-all  # format and validate terraform code
.PHONY: terraform-deploy-dev  # deploy to develop environment
.PHONY: terraform-destroy-dev  # destroy the develop environment
.PHONY: terraform-deploy-prod  # deploy to production environment
.PHONY: terraform-destroy-prod  # destroy the production environment
.PHONY: terraform-clean # removes local created terraform resources

SHELL := /bin/bash

SYSTEMS_DOCKER = app
SYSTEMS = ${SYSTEMS_DOCKER}

SYSTEMS_INSTALL = $(SYSTEMS:%=install-%)
SYSTEMS_CLEAN = $(SYSTEMS:%=clean-%)
SYSTEMS_LINT = $(SYSTEMS:%=lint-%)
SYSTEMS_TEST = $(SYSTEMS:%=test-%)
SYSTEMS_FORMAT = $(SYSTEMS:%=format-%)
SYSTEMS_FIX = $(SYSTEMS:%=fix-%)
SYSTEMS_LOCK = $(SYSTEMS:%=lock-%)
SYSTEMS_UPGRADE = $(SYSTEMS:%=upgrade-%)
SYSTEMS_DOCKER_BUILD = $(SYSTEMS_DOCKER:%=docker-build-%)
SYSTEMS_ALL = $(SYSTEMS:%=all-%)

INTERACTIVE_FLAG := $(shell [ -t 0 ] && echo "-it")
SSH_SETTINGS=-v ~/.ssh:/root/.ssh:ro -v ~/.ssh/known_hosts:/root/.ssh/known_hosts:ro
LOCAL_HOST_UID := $(shell id -u)
DOCKER_SOCKET_SETTINGS := $(shell if [ -S /run/user/${LOCAL_HOST_UID}/docker.sock ]; then echo "-v /run/user/${LOCAL_HOST_UID}/docker.sock:/var/run/docker.sock:ro"; else echo "-v /var/run/docker.sock:/var/run/docker.sock"; fi)
TERRAFORM_BASE_COMMAND=docker run --rm ${INTERACTIVE_FLAG} --env-file .env -v $(PWD):/work -w /work/infrastructure ${DOCKER_SOCKET_SETTINGS} ${SSH_SETTINGS} terraform:latest

all: $(SYSTEMS_ALL)
	@echo "** $@ Finished Successfully **"
$(SYSTEMS_ALL):
	@echo $@
	@cd $(@:all-%=%) && make $(MAKE_FLAGS) all

install: $(SYSTEMS_INSTALL)
	@echo "** $@ Finished Successfully **"
$(SYSTEMS_INSTALL):
	@echo $@
	@cd $(@:install-%=%) && make $(MAKE_FLAGS) install

lock: $(SYSTEMS_LOCK)
	@echo "** $@ Finished Successfully **"
$(SYSTEMS_LOCK):
	@echo $@
	@cd $(@:lock-%=%) && make $(MAKE_FLAGS) lock

upgrade: $(SYSTEMS_UPGRADE)
	@echo "** $@ Finished Successfully **"
$(SYSTEMS_UPGRADE):
	@echo $@
	@cd $(@:upgrade-%=%) && make $(MAKE_FLAGS) upgrade

lint: $(SYSTEMS_LINT)
	@echo "** $@ Finished Successfully **"
$(SYSTEMS_LINT):
	@echo $@
	@cd $(@:lint-%=%) && make $(MAKE_FLAGS) lint

format: $(SYSTEMS_FORMAT)
	@echo "** $@ Finished Successfully **"
$(SYSTEMS_FORMAT):
	@echo $@
	@cd $(@:format-%=%) && make $(MAKE_FLAGS) format

fix: $(SYSTEMS_FIX)
	@echo "** $@ Finished Successfully **"
$(SYSTEMS_FIX):
	@echo $@
	@cd $(@:fix-%=%) && make $(MAKE_FLAGS) fix

test: $(SYSTEMS_TEST)
	@echo "** $@ Finished Successfully **"
$(SYSTEMS_TEST):
	@echo $@
	@cd $(@:test-%=%) && make $(MAKE_FLAGS) test

clean: $(SYSTEMS_CLEAN)
	@echo "** $@ Finished Successfully **"
$(SYSTEMS_CLEAN):
	@echo $@
	@cd $(@:clean-%=%) && make $(MAKE_FLAGS) clean

docker-build: $(SYSTEMS_DOCKER_BUILD)
	@echo "** $@ Finished Successfully **"
$(SYSTEMS_DOCKER_BUILD):
	@echo $@
	@cd $(@:docker-build-%=%) && make $(MAKE_FLAGS) docker-build

terraform-docker-build:
	DOCKER_BUILDKIT=1 docker build infrastructure -t terraform:latest

terraform-setup: terraform-docker-build
	$(TERRAFORM_BASE_COMMAND) init -backend-config=environments/${ENVIRONMENT}/backend.conf

terraform-upgrade: terraform-docker-build
	$(TERRAFORM_BASE_COMMAND) init -upgrade -backend-config=environments/${ENVIRONMENT}/backend.conf

terraform-fix:
	$(MAKE) terraform-setup ENVIRONMENT=dev
	$(TERRAFORM_BASE_COMMAND) fmt -recursive

terraform-validate:
	$(MAKE) terraform-setup ENVIRONMENT=$(ENVIRONMENT)
	$(TERRAFORM_BASE_COMMAND) fmt -check -recursive -diff
	$(TERRAFORM_BASE_COMMAND) validate

terraform-all:
	$(MAKE) terraform-fix
	$(MAKE) terraform-validate ENVIRONMENT=dev

terraform-base:
	$(MAKE) terraform-setup
	$(TERRAFORM_BASE_COMMAND) ${COMMAND} -var-file=environments/${ENVIRONMENT}/variables.tfvars

terraform-deploy-dev:
	$(MAKE) terraform-base ENVIRONMENT=dev COMMAND="apply ${DEPLOY_COMMAND_EXTENSION}"

terraform-destroy-dev:
	$(MAKE) terraform-base ENVIRONMENT=dev COMMAND="destroy"

terraform-deploy-prod:
	$(MAKE) terraform-base ENVIRONMENT=prod COMMAND="apply ${DEPLOY_COMMAND_EXTENSION}"

terraform-destroy-prod:
	$(MAKE) terraform-base ENVIRONMENT=prod COMMAND="destroy"

terraform-clean:
	find . -type d -name '.terraform' -exec rm -rf {} +
	find . -type f -name '.terraform.lock.hcl' -delete

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
.PHONY: terraform-format  # format terraform code
.PHONY: terraform-validate  # validate terraform code
.PHONY: terraform-all  # format and validate terraform code
.PHONY: terraform-reconfigure # terraform init -reconfigure
.PHONY: terraform-deploy-dev  # deploy to develop environment
.PHONY: terraform-destroy-dev  # destroy the develop environment
.PHONY: terraform-deploy-prod  # deploy to production environment
.PHONY: terraform-destroy-prod  # destroy the production environment
.PHONY: terraform-clean # removes local created terraform resources
.PHONY: gcloud-set-project # set gcloud default project (host)
.PHONY: gcloud-adc-login # gcloud application default login (host)
.PHONY: gcloud-login # gcloud login (host)

SHELL := /bin/bash

SYSTEMS_DOCKER = app
SYSTEMS = ${SYSTEMS_DOCKER}
ENVIRONMENT ?= dev

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
GCP_ADC_SETTINGS := -v ~/.config/gcloud:/root/.config/gcloud:rw
# Optional: set GOOGLE_APPLICATION_CREDENTIALS to a JSON file path and it will be mounted as-is.
CREDENTIALS_PATH ?= $(GOOGLE_APPLICATION_CREDENTIALS)
GCP_CREDENTIALS_SETTINGS := $(shell if [ -n "$(CREDENTIALS_PATH)" ]; then echo "-v $(CREDENTIALS_PATH):$(CREDENTIALS_PATH):ro"; fi)
TERRAFORM_BASE_COMMAND=docker run --rm ${INTERACTIVE_FLAG} --env-file .env -v $(PWD):/work -w /work/infrastructure ${DOCKER_SOCKET_SETTINGS} ${SSH_SETTINGS} ${GCP_ADC_SETTINGS} ${GCP_CREDENTIALS_SETTINGS} terraform:latest

define SYSTEM_TARGET
$1: $2
	@echo "** $$@ Finished Successfully **"
$2:
	@echo $$@
	@cd $$(@:$1-%=%) && make $$(MAKE_FLAGS) $1
endef

$(eval $(call SYSTEM_TARGET,all,$(SYSTEMS_ALL)))
$(eval $(call SYSTEM_TARGET,install,$(SYSTEMS_INSTALL)))
$(eval $(call SYSTEM_TARGET,lock,$(SYSTEMS_LOCK)))
$(eval $(call SYSTEM_TARGET,upgrade,$(SYSTEMS_UPGRADE)))
$(eval $(call SYSTEM_TARGET,lint,$(SYSTEMS_LINT)))
$(eval $(call SYSTEM_TARGET,format,$(SYSTEMS_FORMAT)))
$(eval $(call SYSTEM_TARGET,fix,$(SYSTEMS_FIX)))
$(eval $(call SYSTEM_TARGET,test,$(SYSTEMS_TEST)))
$(eval $(call SYSTEM_TARGET,clean,$(SYSTEMS_CLEAN)))
$(eval $(call SYSTEM_TARGET,docker-build,$(SYSTEMS_DOCKER_BUILD)))

terraform-docker-build:
	DOCKER_BUILDKIT=1 docker build infrastructure -t terraform:latest

terraform-setup: terraform-docker-build
	$(TERRAFORM_BASE_COMMAND) init -backend-config=environments/${ENVIRONMENT}/backend.conf

terraform-reconfigure: terraform-docker-build
	$(TERRAFORM_BASE_COMMAND) init -backend-config=environments/${ENVIRONMENT}/backend.conf -reconfigure

terraform-upgrade: terraform-docker-build
	$(TERRAFORM_BASE_COMMAND) init -upgrade -backend-config=environments/${ENVIRONMENT}/backend.conf

terraform-format:
	$(MAKE) terraform-setup ENVIRONMENT=$(ENVIRONMENT)
	$(TERRAFORM_BASE_COMMAND) fmt -recursive

terraform-validate:
	$(MAKE) terraform-setup ENVIRONMENT=$(ENVIRONMENT)
	$(TERRAFORM_BASE_COMMAND) fmt -check -recursive -diff
	$(TERRAFORM_BASE_COMMAND) validate

terraform-all:
	$(MAKE) terraform-format ENVIRONMENT=$(ENVIRONMENT)
	$(MAKE) terraform-validate ENVIRONMENT=$(ENVIRONMENT)

terraform-base:
	$(MAKE) terraform-setup ENVIRONMENT=$(ENVIRONMENT)
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

gcloud-set-project:
	@if [ -z "$(PROJECT_ID)" ]; then echo "PROJECT_ID is required. Example: make gcloud-set-project PROJECT_ID=your-project"; exit 1; fi
	gcloud config set project $(PROJECT_ID)

gcloud-login:
	gcloud auth login
	gcloud auth application-default login

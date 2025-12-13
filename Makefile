.PHONY: help setup test lint format clean build deploy

help:
	@echo "podcast-automator - Development Commands"
	@echo ""
	@echo "setup              - Setup development environment"
	@echo "test               - Run all tests with coverage"
	@echo "test-fetch         - Run fetch-job tests"
	@echo "test-process       - Run process-job tests"
	@echo "test-upload        - Run upload-job tests"
	@echo "test-notify        - Run notify-job tests"
	@echo "lint               - Run linters (ruff, mypy, pylint)"
	@echo "format             - Format code (black, ruff)"
	@echo "clean              - Clean build artifacts"
	@echo "build              - Build all Docker images"
	@echo "deploy             - Deploy to GCP (requires Terraform)"
	@echo ""

# Setup
setup:
	@echo "Setting up development environment..."
	pip install -e app/shared/
	pip install -r app/controller/requirements.txt
	pip install -r app/fetch-job/requirements.txt
	pip install -r app/process-job/requirements.txt
	pip install -r app/upload-job/requirements.txt
	pip install -r app/notify-job/requirements.txt
	pip install -r pyproject.toml[dev]
	@echo "✅ Setup complete!"

# Testing
test:
	@echo "Running all tests..."
	pytest app/ -v --cov=app/shared --cov-report=html

test-fetch:
	@echo "Testing fetch-job..."
	pytest app/fetch-job/tests/ -v

test-process:
	@echo "Testing process-job..."
	pytest app/process-job/tests/ -v

test-upload:
	@echo "Testing upload-job..."
	pytest app/upload-job/tests/ -v

test-notify:
	@echo "Testing notify-job..."
	pytest app/notify-job/tests/ -v

# Linting & Formatting
lint:
	@echo "Running linters..."
	ruff check app/
	mypy app/shared/ --ignore-missing-imports
	pylint app/ || true

format:
	@echo "Formatting code..."
	ruff check app/ --fix
	black app/

# Cleanup
clean:
	@echo "Cleaning up..."
	find app -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find app -type f -name '*.pyc' -delete
	rm -rf htmlcov/ .coverage .mypy_cache/
	@echo "✅ Cleanup complete!"

# Docker Build
build:
	@echo "Building Docker images..."
	docker build -t podcast-processor:controller app/controller/
	docker build -t podcast-processor:fetch-job app/fetch-job/
	docker build -t podcast-processor:process-job app/process-job/
	docker build -t podcast-processor:upload-job app/upload-job/
	docker build -t podcast-processor:notify-job app/notify-job/
	@echo "✅ Build complete!"

build-push: build
	@echo "Pushing images to registry..."
	PROJECT_ID?=$(shell gcloud config get-value project)
	docker tag podcast-processor:controller gcr.io/$${PROJECT_ID}/controller:latest
	docker tag podcast-processor:fetch-job gcr.io/$${PROJECT_ID}/fetch-job:latest
	docker tag podcast-processor:process-job gcr.io/$${PROJECT_ID}/process-job:latest
	docker tag podcast-processor:upload-job gcr.io/$${PROJECT_ID}/upload-job:latest
	docker tag podcast-processor:notify-job gcr.io/$${PROJECT_ID}/notify-job:latest
	docker push gcr.io/$${PROJECT_ID}/controller:latest
	docker push gcr.io/$${PROJECT_ID}/fetch-job:latest
	docker push gcr.io/$${PROJECT_ID}/process-job:latest
	docker push gcr.io/$${PROJECT_ID}/upload-job:latest
	docker push gcr.io/$${PROJECT_ID}/notify-job:latest
	@echo "✅ Push complete!"

# Terraform
tf-init:
	@echo "Initializing Terraform..."
	cd terraform && terraform init -backend-config="bucket=podcast-automator-tfstate" -backend-config="prefix=podcast-automator"

tf-plan:
	@echo "Planning Terraform deployment..."
	cd terraform && terraform plan -var-file="terraform.tfvars" -out=tfplan

tf-apply:
	@echo "Applying Terraform deployment..."
	cd terraform && terraform apply tfplan

deploy: build-push tf-apply
	@echo "✅ Deployment complete!"

# Dev Container
devcontainer-build:
	@echo "Building Dev Container..."
	devcontainer build --workspace-folder .

devcontainer-open:
	@echo "Opening in Dev Container..."
	code .

.DEFAULT_GOAL: help

help:
	@echo "Available commands:"
	@echo
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'


api:  ## Start API Gateway locally (port 3000)
	DOCKER_HOST=unix:///home/daniel/.docker/desktop/docker.sock sam local start-api --env-vars env.json

build:  ## Build the app
	DOCKER_HOST=unix:///home/daniel/.docker/desktop/docker.sock sam build --use-container

deploy:  ## Deploy to AWS
	sam deploy

dynamo:  ## Start DynamoDB locally (port 8000)
	docker run -p 8000:8000 amazon/dynamodb-local

cloud-test: ## Run integration tests against cloud API
	API_HOST="aws" pytest ./tests/integration -v

local-test:  ## Run integration test against local API
	API_HOST="localhost" pytest ./tests/integration -v

unit-test:  ## Run unit tests
	pytest ./tests/unit -v
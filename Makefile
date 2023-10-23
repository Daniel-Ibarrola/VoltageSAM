.DEFAULT_GOAL: help

help:
	@echo "Available commands:"
	@echo
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'


api:  ## Start API Gateway locally (port 3000)
	DOCKER_HOST=unix:///home/daniel/.docker/desktop/docker.sock sam local start-api --env-vars env.json --docker-network voltage-api-net

build:  ## Build the app
	DOCKER_HOST=unix:///home/daniel/.docker/desktop/docker.sock sam build --use-container

build-dynamo:  ## Create a container for local DynamoDB
	docker run -p 8000:8000 --network voltage-api-net --name dynamo-local amazon/dynamodb-local

deploy:  ## Deploy to AWS
	sam deploy

dynamo:  ## Start DynamoDB locally (port 8000)
	docker start dynamo-local

network:  ## Create network for docker containers
	docker network create voltage-api-net

cloud-test: ## Run integration tests against cloud API
	API_HOST="aws" pytest ./tests/integration -v

local-test:  ## Run integration test against local API
	API_HOST="localhost" pytest ./tests/integration -v

unit-test:  ## Run unit tests
	pytest ./tests/unit -v
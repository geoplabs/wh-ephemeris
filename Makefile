.PHONY: up down logs seed test

up:
	docker compose up --build -d

down:
	docker compose down -v

logs:
	docker compose logs -f --tail=100

seed: ## create S3 bucket + SQS queue in LocalStack
	docker compose exec -T -e AWS_REGION=us-east-1 -e AWS_ENDPOINT_URL=http://localstack:4566 api python -m api.scripts.init_localstack

test:
	docker compose exec -T api pytest -q

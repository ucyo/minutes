.PHONY: build test rebuild clean shell push dry-run

build:
	docker compose build test

test: build
	docker compose run --rm test

rebuild:
	docker compose build --no-cache test
	docker compose run --rm test

shell: build
	docker compose run --rm test bash

clean:
	docker compose down --rmi local --volumes --remove-orphans

dry-run: build
	docker compose run --rm \
		-v $(PWD)/.pypirc:/root/.pypirc:ro \
		test bash -c "rm -rf dist/ && python -m build && twine check dist/* && twine upload --repository testpypi dist/*"

push: build
	docker compose run --rm \
		-v $(PWD)/.pypirc:/root/.pypirc:ro \
		test bash -c "rm -rf dist/ && python -m build && twine check dist/* && twine upload dist/*"

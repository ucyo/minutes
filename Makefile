.PHONY: build test rebuild clean shell

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

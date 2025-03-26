install:
	pip install -r requirements.txt
	curl --proto '=https' --tlsv1.2 -fsSL https://get.opentofu.org/install-opentofu.sh | bash -s -- --install-method standalone

dev:
	pip install pytest ruff
	pip install -e .

db:
	docker run --name pg-db -e POSTGRES_USER=admin -e POSTGRES_PASSWORD=adminpass -e POSTGRES_DB=swarmchestrate -p 5432:5432 -d postgres

.PHONY: install, db, dev

.PHONY: install dev test coverage run reset-data

install:
	python -m pip install -r requirements-dev.txt

dev:
	uvicorn app.main:app --reload

run:
	uvicorn app.main:app --host 0.0.0.0 --port 8000

test:
	pytest

coverage:
	pytest --cov=app --cov-report=term-missing

reset-data:
	rm -f data/office_desk_utilization.sqlite3
	python -m app.seed

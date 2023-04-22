PHONY: status

style:
	isort --profile=black ./*.py
	black ./*.py
	flake8 --ignore=E501,W503,F403,F405 --exclude=ordinals-collections,alembic .

check:
	flake8 --ignore=E501,W503,F403,F405 --exclude=ordinals-collections,alembic .

status:
	./status.sh

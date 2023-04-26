PHONY: status

style:
	isort --profile=black ./*.py
	black ./*.py
	flake8 --ignore=E501,W503,F403,F405 .

check:
	isort --profile=black ./*.py --check
	black ./*.py --check
	flake8 --ignore=E501,W503,F403,F405 .

status:
	./status.sh

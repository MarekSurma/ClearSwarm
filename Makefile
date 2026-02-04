.PHONY: install test lint format clean help

help:
	@echo "Available commands:"
	@echo "  make install       - Install package in development mode"
	@echo "  make install-dev   - Install with development dependencies"
	@echo "  make test          - Run tests with pytest"
	@echo "  make lint          - Run code linters (flake8, pylint, mypy)"
	@echo "  make format        - Format code with black and isort"
	@echo "  make clean         - Remove build artifacts and cache files"
	@echo "  make run           - Run agent (usage: make run AGENT=name MESSAGE='text')"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"
	pip install -r requirements-dev.txt

test:
	pytest

lint:
	flake8 src/ tests/
	pylint src/
	mypy src/

format:
	black src/ tests/
	isort src/ tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf build/ dist/ *.egg-info .coverage htmlcov/ .pytest_cache/ .mypy_cache/

run:
	@if [ -z "$(AGENT)" ] || [ -z "$(MESSAGE)" ]; then \
		echo "Usage: make run AGENT=agent_name MESSAGE='your message'"; \
		exit 1; \
	fi
	python -m multi_agent $(AGENT) "$(MESSAGE)"

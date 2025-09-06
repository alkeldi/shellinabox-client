# Variables
PYTHON := python3
PYLINT := $(PYTHON) -m pylint

# Default target
all: lint

# Linter Target
.PHONY: lint
lint:
	@echo "Running pylint..."	
	$(PYLINT) $(shell git ls-files '*.py')

# Clean target
.PHONY: clean
clean:
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} +

# Help Target
.PHONY: help
help:
	@echo "Available targets:"
	@echo "  lint   - Runs pylint on all Python files"
	@echo "  clean  - Removes generated files and caches"
	@echo "  help   - Displays this help message"

# Variables
PYTHON := python3
PYLINT := $(PYTHON) -m pylint
DOCKER := docker
CONTAINER_IMAGE := ubuntu
CONTAINER_PORT := 5555
CONTAINER_CMD := echo 'root:root' | chpasswd;
CONTAINER_CMD := $(CONTAINER_CMD) apt update;
CONTAINER_CMD := $(CONTAINER_CMD) apt install -y openssl shellinabox;
CONTAINER_CMD := $(CONTAINER_CMD) /usr/bin/shellinaboxd
CONTAINER_CMD := $(CONTAINER_CMD) --debug
CONTAINER_CMD := $(CONTAINER_CMD) --no-beep
CONTAINER_CMD := $(CONTAINER_CMD) --disable-peer-check
CONTAINER_CMD := $(CONTAINER_CMD) -u shellinabox
CONTAINER_CMD := $(CONTAINER_CMD) -g shellinabox
CONTAINER_CMD := $(CONTAINER_CMD) -c /var/lib/shellinabox
CONTAINER_CMD := $(CONTAINER_CMD) -p $(CONTAINER_PORT)

# Default target
all: lint

# Linter Target
.PHONY: lint
lint:
	@echo "Running pylint..."	
	$(PYLINT) $(shell git ls-files '*.py')

.PHONY: container
container:
	@echo "Running shellinabox container on port $(CONTAINER_PORT)..."
	$(DOCKER) run --name shellinabox --rm -p $(CONTAINER_PORT):$(CONTAINER_PORT) $(CONTAINER_IMAGE) /bin/bash -c "$(CONTAINER_CMD)"

# Clean target
.PHONY: clean
clean:
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} +

# Help Target
.PHONY: help
help:
	@echo "Available targets:"
	@echo "  container - Runs shellinabox test container on port $(CONTAINER_PORT)"
	@echo "  lint      - Runs pylint on all Python files"
	@echo "  clean     - Removes generated files and caches"
	@echo "  help      - Displays this help message"

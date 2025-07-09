# Makefile for docker-swarm-ctl CLI

BINARY_NAME=docker-swarm-ctl
VERSION=$(shell git describe --tags --always --dirty)
GIT_COMMIT=$(shell git rev-parse HEAD)
BUILD_DATE=$(shell date -u +'%Y-%m-%dT%H:%M:%SZ')
LDFLAGS=-ldflags "-X github.com/docker-swarm-ctl/cli/cmd.Version=$(VERSION) -X github.com/docker-swarm-ctl/cli/cmd.GitCommit=$(GIT_COMMIT) -X github.com/docker-swarm-ctl/cli/cmd.BuildDate=$(BUILD_DATE)"

.PHONY: all build clean test install fmt vet

all: build

build:
	@echo "Building $(BINARY_NAME)..."
	go build $(LDFLAGS) -o $(BINARY_NAME) .

install:
	@echo "Installing $(BINARY_NAME)..."
	go install $(LDFLAGS) .

clean:
	@echo "Cleaning..."
	go clean
	rm -f $(BINARY_NAME)

test:
	@echo "Running tests..."
	go test -v ./...

fmt:
	@echo "Formatting code..."
	go fmt ./...

vet:
	@echo "Running go vet..."
	go vet ./...

deps:
	@echo "Downloading dependencies..."
	go mod download
	go mod tidy

# Build for multiple platforms
build-all: build-linux build-darwin build-windows

build-linux:
	@echo "Building for Linux..."
	GOOS=linux GOARCH=amd64 go build $(LDFLAGS) -o $(BINARY_NAME)-linux-amd64 .
	GOOS=linux GOARCH=arm64 go build $(LDFLAGS) -o $(BINARY_NAME)-linux-arm64 .

build-darwin:
	@echo "Building for macOS..."
	GOOS=darwin GOARCH=amd64 go build $(LDFLAGS) -o $(BINARY_NAME)-darwin-amd64 .
	GOOS=darwin GOARCH=arm64 go build $(LDFLAGS) -o $(BINARY_NAME)-darwin-arm64 .

build-windows:
	@echo "Building for Windows..."
	GOOS=windows GOARCH=amd64 go build $(LDFLAGS) -o $(BINARY_NAME)-windows-amd64.exe .

# Development helpers
run: build
	./$(BINARY_NAME)

dev-setup:
	@echo "Setting up development environment..."
	go mod download
	go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest

lint:
	@echo "Running linter..."
	golangci-lint run

.DEFAULT_GOAL := build
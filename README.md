# Ariadne

A process mining tool that discovers and analyzes process models from OpenTelemetry traces in microservices.

## What it does

Ariadne extracts distributed traces, mines process models from them, and checks how well real-world behavior conforms to those models.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

## Install

```bash
uv sync
```

## Usage

```bash
# Discover process models from trace data
ariadne mine traces.csv --output model

# Check conformance of traces against a model
ariadne check traces.csv model

# Visualize a discovered model set
ariadne inspect model

# Import traces from Elastic APM
ariadne import from-elastic export.csv --output traces.csv

# Collect traces from an OpenTelemetry backend
ariadne collect
```

## Architecture

Ariadne uses a plugin-based architecture. Mining algorithms and conformance checkers are registered via Python entry points, making it easy to add custom implementations.

The `ariadne-pm4py-plugins` package provides built-in algorithms backed by [PM4Py](https://pm4py.fit.fraunhofer.de/).

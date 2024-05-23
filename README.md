---
title: MergeUI
emoji: 🧬
colorFrom: purple
colorTo: pink
sdk: gradio
sdk_version: 4.31.5
python_version: 3.9
app_file: mergeui/web/gradio_app/main.py
fullWidth: true
startup_duration_timeout: 1h
license: apache-2.0
language:
  - en
datasets:
  - open-llm-leaderboard/results
tags:
  - merge
  - leaderboard
  - mergekit
  - lazymergekit
short_description: All-in-one UI for merged LLMs in Hugging Face Hub
thumbnail: https://raw.githubusercontent.com/naskio/mergeui/main/static/brand/banner.svg
pinned: true
---

[![MergeUI](./static/brand/banner.svg)](https://naskio-mergeui.hf.space)
<h3 align="center">All-in-one UI for merged LLMs in Hugging Face Hub</h3>

[MergeUI](https://naskio-mergeui.hf.space) is an [open-source project](https://github.com/naskio/mergeui) that aims to
provide a user-friendly interface for discovering and analyzing merged large language models (Merged LLMs) from
the [Hugging Face Hub](https://huggingface.co/models?other=merge&sort=trending).
It is particularly focused on models that have been merged using [MergeKit](https://github.com/arcee-ai/mergekit).

# Development

## Requirements

To run the project locally, you need to have the following installed:

- [Python 3.9+](https://www.python.org/)
- [Poetry 1.8+](https://python-poetry.org/)
- [Graphviz](https://www.graphviz.org/download/#mac)
- [Docker](https://www.docker.com/) with [Docker Compose](https://docs.docker.com/compose/)

## Setup

Once you have the requirements installed, you can set up the project by running the following commands:

```shell
poetry install
```

Once the dependencies are installed, make sure to set up the environment variables by creating a `.env` file

```shell
cp .env.example .env
```

> [!TIP]
> Find more about the environment variables in the [settings.py](./mergeui/core/settings.py) file.

Next, we need to launch the database and Redis using Docker Compose:

```shell
docker compose up -d
```

> [!TIP]
> run `docker compose down` to stop these services when you are done.

## Run

> [!NOTE]
> This project use `poetry` with `Poe the Poet` plugin to run commands, run `poe` to see all available commands.

Once the setup is complete, we need to index the models from the Hugging Face Hub and store them in the database.

### Indexing

For indexing models we use [RQ](https://python-rq.org/):

- First we need to launch some workers by running the following command in separate terminal tabs:
  ```shell
  poe worker
  ```
- Next, we can start the indexing process by running:
  ```shell
  poe index
  ```
- To monitor the indexing process, we can use the RQ dashboard by running:
  ```shell
  rq-dashboard
  ```

> [!IMPORTANT]
> The indexing process takes few minutes to complete depending on your resources, number of workers and number
> of `merge` models available.

> [!NOTE]
> It takes around 6 minutes to index a graph of ~12k models and ~51k relationships using 64 workers.

### Visualisation

Once the indexing process is complete, we can start our app using the following command:

#### FastAPI server with a Gradio app

```shell
uvicorn mergeui.main:app --port 8000 --log-level trace
```

#### FastAPI only (dev mode)

> [!WARNING]
> Set environment variable `GRADIO_APP_DISABLED` to `true` to disable Gradio app.

```shell
uvicorn mergeui.main:app --reload --port 8000 --log-level debug
```

#### Gradio app only (dev mode)

```shell
gradio mergeui/web/gradio_app/main.py # with reloading
python mergeui/web/gradio_app/main.py # without reloading
```

#### Bokeh server (dev mode)

```shell
poe bokeh_dev
```

## Testing

This project use pytest for testing, you can run the tests using the following command:

```shell
poe test
```

## Contributing

MergeUI is a new project, and any contribution would make a difference! Whether you find a bug, have valuable feedback
or suggestions, or simply want to get involved, we would love to hear from you!
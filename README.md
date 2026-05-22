# TextQueue

TextQueue is a small FastAPI + Celery project that demonstrates how to queue a
background text-generation job and poll for the result later.

The API accepts a topic, sends the work to a Celery worker through Redis, and
returns a task id immediately. The worker then simulates a longer-running
paragraph generation task and stores the result in Redis.

## Tech Stack

- FastAPI for the HTTP API
- Celery for background task processing
- Redis as the Celery broker and result backend
- Docker Compose for running the API, worker, and Redis together

## Project Structure

```text
.
+-- main.py                  # FastAPI routes
+-- src/
|   +-- celery_worker.py     # Celery app configuration
|   +-- task.py              # Celery task definitions
+-- docker-compose.yml       # Redis, FastAPI, and Celery worker services
+-- dockerfile               # Python image used by the services
+-- requirements.txt
+-- pyproject.toml
```

## How It Works

1. A client calls `POST /generate/{topic}`.
2. FastAPI calls `generate_paragraph.delay(topic)`.
3. Celery puts the task message on Redis.
4. The Celery worker receives the task and executes `generate_paragraph`.
5. A client calls `GET /result/{task_id}` to check the task status and result.

## Run With Docker Compose

Start all services:

```bash
docker compose up --build
```

The API will be available at:

```text
http://localhost:8000
```

Open the interactive API docs at:

```text
http://localhost:8000/docs
```

## API Endpoints

### Health Check

```http
GET /
```

Example response:

```json
{
  "message": "Paragraph Generator API"
}
```

### Queue a Paragraph Generation Task

```http
POST /generate/{topic}
```

Example:

```bash
curl -X POST http://localhost:8000/generate/celery
```

Example response:

```json
{
  "task_id": "your-task-id",
  "status": "Processing started"
}
```

### Get Task Result

```http
GET /result/{task_id}
```

Example:

```bash
curl http://localhost:8000/result/your-task-id
```

Possible statuses include:

- `PENDING`: Celery does not yet have a result for the task.
- `STARTED`: The worker has started processing the task.
- `SUCCESS`: The task completed successfully.
- `FAILURE`: The task failed while executing, or Celery could not resolve the task properly.

## Celery Configuration

The Celery app is created in `src/celery_worker.py`:

```python
celery = Celery(
    "tasks",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0",
    include=["src.task"],
)
```

The important part is:

```python
include=["src.task"]
```

That line tells the Celery worker to import the module where the task is
defined. Without importing the task module, Celery may receive a task message
but not know which function should handle it.

The worker is started in `docker-compose.yml` with:

```bash
celery -A src.celery_worker.celery worker --loglevel=info
```

This points Celery to the `celery` object inside `src/celery_worker.py`.

## The Task Registration Issue I Ran Into

One confusing issue in this project was that the task was not being registered
with Celery correctly.

The difficult part was that it did not produce a clear error in the FastAPI
request. The API could still create a task id, and Redis could still receive the
message, but the result endpoint would eventually show a failure status or never
produce the expected output. That made it look like the task was running and
failing silently, when the real issue was that the Celery worker did not know
about the task function.

In Celery, defining a task with `@celery.task` is not enough by itself if the
worker never imports that module. The worker has to load the module containing
the task before it can register it.

In this project, the task lives in:

```text
src/task.py
```

So the Celery app includes it explicitly:

```python
include=["src.task"]
```

The task is also imported by FastAPI in `main.py`:

```python
from src.task import generate_paragraph
```

That import lets the API call `generate_paragraph.delay(topic)`, but the worker
still needs its own import path because the worker is a separate process.

### Things to Check When a Celery Task Is Not Registered

- Make sure the worker command uses the correct Celery app path:

  ```bash
  celery -A src.celery_worker.celery worker --loglevel=info
  ```

- Make sure the task module is imported by the worker, either through
  `include=["src.task"]` or Celery autodiscovery.

- Make sure the task decorator uses the same Celery app that the worker starts:

  ```python
  from src.celery_worker import celery

  @celery.task
  def generate_paragraph(topic):
      ...
  ```

- Check the worker logs when it starts. Registered tasks should appear in the
  worker output. If `src.task.generate_paragraph` is missing, the worker has not
  loaded the task module.

- Rebuild and restart containers after changing imports or Celery config:

  ```bash
  docker compose down
  docker compose up --build
  ```

## Local Development Notes

If running outside Docker, Redis must be available locally and the broker URL in
`src/celery_worker.py` may need to change from:

```text
redis://redis:6379/0
```

to:

```text
redis://localhost:6379/0
```

Then run the API and worker in separate terminals:

```bash
uvicorn main:app --reload
```

```bash
celery -A src.celery_worker.celery worker --loglevel=info
```

## Notes

The Docker Compose file overrides the Dockerfile command for both the FastAPI
and worker containers. For this project, use the commands in
`docker-compose.yml` as the source of truth.

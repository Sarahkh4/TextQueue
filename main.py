from fastapi import FastAPI
from src.task import generate_paragraph
from celery.result import AsyncResult
from src.celery_worker import celery

app = FastAPI()
@app.get("/")
def home():
    return {"message": "Paragraph Generator API"}
@app.post("/generate/{topic}")
def generate(topic: str):

    task = generate_paragraph.delay(topic)

    return {
        "task_id": task.id,
        "status": "Processing started"
    }
@app.get("/result/{task_id}")
def get_result(task_id: str):
    task = AsyncResult(task_id, app=celery)
    return {
        "task_id": task.id,
        "status": task.status,
        "result": task.result
    }
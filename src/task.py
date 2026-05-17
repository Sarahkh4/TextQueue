from celery_worker import celery
import time

@celery.task
def generate_paragraph(topic):

    print(f"Generating paragraph about: {topic}")

    # simulate heavy processing
    time.sleep(5)

    paragraph = f"""
    {topic} is an important topic in modern technology.
    It has many applications and helps improve efficiency,
    scalability, and automation in software systems.
    """

    return paragraph
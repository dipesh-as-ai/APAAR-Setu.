# APAAR Setu Worker

The prototype processing job currently runs through FastAPI `BackgroundTasks` so it can run without Docker or a broker. This directory is the extraction boundary for Celery or another durable worker when production-scale processing is introduced.

FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY run.py .
ENV DATABASE_URL=sqlite:////data/arenaplant.db
VOLUME /data
EXPOSE 8000 8100 5020
CMD ["python", "run.py"]

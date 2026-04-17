FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN test -d agent || (echo "ERROR: agent/ directory not found. Did you forget to push code to GitHub?" && exit 1)
RUN test -d config || (echo "ERROR: config/ directory not found. Did you forget to push code to GitHub?" && exit 1)
EXPOSE 8000
CMD ["uvicorn", "agent.main:app", "--host", "0.0.0.0", "--port", "8000"]

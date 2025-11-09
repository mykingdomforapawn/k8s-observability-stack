# Specifies the lightweight Python 3.11 base image.
FROM python:3.11-slim

# Sets the working directory inside the container to /app.
WORKDIR /app

# Copies the dependency file and installs packages.
# Done before copying app code to leverage Docker layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copies the main application source code into the container.
COPY main.py .

# Documents that the container listens on port 8000.
EXPOSE 8000

# Defines the command to start the application server (Uvicorn).
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

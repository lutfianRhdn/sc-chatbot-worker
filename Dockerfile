# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables to prevent Python from writing .pyc files
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install git
RUN apt-get update && apt-get install -y git && apt-get clean

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install nltk

# Copy the rest of the application code into the container
COPY . .

# Expose the port that the Flask application will run on
EXPOSE 9100

# Set the command to run the application using Gunicorn
CMD ["python", "src/supervisor.py"]
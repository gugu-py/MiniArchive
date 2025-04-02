# Use the official lightweight Python image
FROM python:3.11-slim

# Set the working directory to /app
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Set environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.py

# Expose port 8080 for the application
EXPOSE 8080

# Use Gunicorn as the application server
# RUN python init.py
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app", "--log-level", "debug"]

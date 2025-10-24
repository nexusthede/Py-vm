# Use official Python 3.11 image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy all files into the container
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port for keep_alive
EXPOSE 8080

# Set environment variable for production
ENV PYTHONUNBUFFERED=1

# Run the bot
CMD ["python", "main.py"]

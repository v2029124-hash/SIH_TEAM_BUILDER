# Use an official, stable Python runtime
FROM python:3.11-slim

# Install the missing libatomic library and Node.js (required by Prisma)
RUN apt-get update && apt-get install -y \
    libatomic1 \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . .

# Generate the Prisma Client securely
RUN prisma generate

# Command to run the application using Gunicorn on Railway's dynamic port
CMD sh -c "gunicorn app:app --bind 0.0.0.0:$PORT"
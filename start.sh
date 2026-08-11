#!/bin/bash
# Generate the Prisma client for the production environment
prisma generate

# Start the Flask app using Gunicorn
gunicorn app:app --bind 0.0.0.0:$PORT
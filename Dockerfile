FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DB_PATH=/data/mstr_state.db
ENV PORT=8080

WORKDIR /app

# Install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Create volume directory
RUN mkdir -p /data

# Copy project files
COPY . /app/

# Expose port (Railway routes external traffic to the port the server listens on)
EXPOSE 8080

CMD ["python", "bot.py"]

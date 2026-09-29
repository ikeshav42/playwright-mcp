# Base image ships Chromium and its system libraries; tag must match the pinned playwright version.
FROM mcr.microsoft.com/playwright/python:v1.63.0-noble

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY browser_mcp.py .

# Run as the unprivileged user provided by the base image.
USER pwuser
ENV BROWSER_MCP_NO_SANDBOX=1 PYTHONUNBUFFERED=1
ENTRYPOINT ["python", "browser_mcp.py"]

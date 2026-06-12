FROM n8nio/n8n:latest

USER root

# Install Python 3 and pre-compiled alpine packages for pandas and requests
# This prevents compilation overhead and "externally-managed-environment" pip errors
RUN apk add --no-cache python3 py3-pandas py3-requests

USER node

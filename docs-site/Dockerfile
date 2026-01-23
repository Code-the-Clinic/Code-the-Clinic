# Use a lightweight Python image
FROM python:3.11-slim

WORKDIR /docs

# Install MkDocs and the Material Theme
RUN pip install mkdocs mkdocs-material

# Expose the port MkDocs runs on
EXPOSE 8000

# Command to run the dev server
# 0.0.0.0 is required for Docker to share the site with your laptop
CMD ["mkdocs", "serve", "--dev-addr=0.0.0.0:8000"]
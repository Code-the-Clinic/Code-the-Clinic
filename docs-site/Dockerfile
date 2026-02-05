# Use a lightweight Python image
FROM python:3.11-slim

WORKDIR /docs

# You can change this local GID/UID if you are running into system permission issues
# But make sure to keep the uid/gid above 1000
RUN addgroup --system --gid 1001 docsgroup && \
    adduser --system --uid 1001 --ingroup docsgroup docsuser

# Install MkDocs and the Material Theme
RUN pip install mkdocs mkdocs-material

# Expose the port MkDocs runs on
EXPOSE 8000

USER docsuser

# Command to run the dev server
# 0.0.0.0 is required for Docker to share the site with your laptop
CMD ["mkdocs", "serve", "--dev-addr=0.0.0.0:8000"]
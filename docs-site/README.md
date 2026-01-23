# Documentation site
Welcome to our documentation site!

## How to Run
- Download and install Docker desktop
    - To confirm that Docker is installed, run docker --version
- Run the docs locally:
    - docker-compose up --build
    - Go to localhost:8001 to see the latest version of the docs

## How to make changes
- Edit the markdown documents (deliverables.md, index.md, team.md) and save changes
- Shut down the container (Ctrl+C) and then run docker-compose up --build again to re-run the container with the new changes
- When you are ready to publish your changes, commit and push to the Git repo
# Python App for Workspace Status

This is a Python-based application that allows you to:

- Visualize the status of a workspace.
- Export the list of items within the workspace, among other features.

Additionally, this repository includes a Dockerfile for containerizing the application, making it easier to run in isolated environments.

## Ports

- The application runs on port `8991`.

## Usage

1. Clone the repository:
    ```bash
    git clone https://github.com/jsantacruzpy/tiaxiom.git
    cd workspace
    ```

2. Build the Docker image:
    ```bash
    docker build -t workspace-app .
    ```

3. Run the Docker container:
    ```bash
    docker run -p 8991:8991 workspace-app
    ```

You can now access the app by visiting `http://localhost:8991` on your browser.

## Requirements

- Python 3.x
- Docker (if you wish to containerize the app)

# GPS Hook

This project is a FastAPI application that serves as a hook for GPS data. It receives data from Kafka, processes it, and broadcasts it to connected clients via WebSockets. It also provides a REST API for retrieving initial data.

## Features

*   **Real-time data broadcasting**: Uses WebSockets to broadcast GPS, sensor, and load data to connected clients in real-time.
*   **Kafka integration**: Consumes data from Kafka topics.
*   **Data enrichment**: Enriches the data with information from a MySQL database and the SmartTyre API.
*   **Alerting system**: Generates alerts for various conditions (e.g., low pressure, high temperature, GPS timeout).
*   **Scalable architecture**: Uses a `ConnectionManager` and a fan-out pattern to handle a large number of WebSocket connections efficiently.
*   **Optimized database insertions**: Limits the number of database insertions to prevent overloading the database.
*   **Leveled logging**: Provides a leveled logging system for easier debugging and monitoring.

## Getting Started

### Prerequisites

*   Python 3.12
*   Docker
*   Docker Compose

### Installation

1.  **Clone the repository:**

    ```bash
    git clone <repository-url>
    cd <repository-name>
    ```

2.  **Create a virtual environment:**

    ```bash
    python -m venv venv
    source venv/bin/activate
    ```

3.  **Install the dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up the environment variables:**

    Create a `.env` file in the root of the project and add the following environment variables:

    ```
    MONGO_DETAILS=mongodb://<user>:<password>@<host>:<port>
    MONGO_DB_NAME=<database-name>
    KAFKA_BOOTSTRAP_SERVERS=<kafka-host>:<kafka-port>
    KAFKA_GROUP_ID=<kafka-group-id>
    SMARTTYRE_BASE_URL=<smarttyre-api-url>
    SMARTTYRE_CLIENT_ID=<smarttyre-client-id>
    SMARTTYRE_CLIENT_SECRET=<smarttyre-client-secret>
    SMARTTYRE_SIGN_KEY=<smarttyre-sign-key>
    MYSQL_USER=<mysql-user>
    MYSQL_PASSWORD=<mysql-password>
    MYSQL_HOST=<mysql-host>
    MYSQL_DB=<mysql-database>
    ```

### Running the Application

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

To run the application in the background, you can use `nohup`:

```bash
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > uvicorn.log 2>&1 &
```

### Running the Tests

```bash
pytest
```

## Architecture

The application is composed of the following components:

*   **FastAPI**: A modern, fast (high-performance), web framework for building APIs with Python 3.7+ based on standard Python type hints.
*   **Uvicorn**: A lightning-fast ASGI server, built on uvloop and httptools.
*   **Kafka**: A distributed streaming platform.
*   **MongoDB**: A NoSQL database.
*   **MySQL**: A relational database.
*   **WebSockets**: A protocol for real-time, two-way communication between clients and servers.

The application follows a modular architecture, with the code organized into the following directories:

*   `app/api`: Contains the API endpoints and WebSocket routes.
*   `app/core`: Contains the core application logic, such as the configuration and logger.
*   `app/db`: Contains the database connection logic.
*   `app/services`: Contains the services for interacting with external APIs.
*   `app/utils`: Contains utility functions.
*   `tests`: Contains the tests.

## API Endpoints

The application provides the following API endpoints:

*   `/init/gps`: Retrieves the last known GPS data for a given company or a specific vehicle.
*   `/init/sensor`: Retrieves the last known sensor data for a given company or a specific vehicle.
*   `/init/load`: Retrieves the last known load data for a given company or a specific vehicle.
*   `/init/alerts`: Retrieves the initial alerts data for a given company.

## WebSocket Channels

The application provides the following WebSocket channels:

*   `/ws/gps`: Broadcasts real-time GPS data.
*   `/ws/load`: Broadcasts real-time load data.
*   `/ws/sensor`: Broadcasts real-time sensor data.
*   `/ws/alerts`: Broadcasts real-time alerts.

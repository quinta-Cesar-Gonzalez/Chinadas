# Instructions to Run the Project

To run the full application, you need to start both the Python service (the server) and the Java service (the client) in separate terminal windows.

---

### 1. Start the Python Service

The Python service acts as the server, listening for messages.

**Terminal 1:**

1.  **Install Dependencies** (if you haven't already):
    ```bash
    pip install -r app/requirements.txt
    ```
    *Note: For running tests, you may also need `pip install pytest httpx pytest-asyncio`.*

2.  **Configure Environment:**
    Create a file named `.env` inside the `app/` directory. This file must contain the connection details for your databases (MongoDB, MySQL) and services (Kafka), based on the template in `app/README.md`.

3.  **Run the Service:**
    From the project's root directory, run the following command:
    ```bash
    uvicorn app.main:app --host 0.0.0.0 --port 8000
    ```

4.  Leave this terminal running. The Python service is now active and waiting for connections.

---

### 2. Start the Java Service

The Java service consumes from Kafka and forwards messages to the Python service.

**Terminal 2:**

1.  **Prerequisites:**
    Ensure you have Java (JDK 8 or higher) and Maven installed.

2.  **Configure Kafka Connection:**
    Open the file `JavaBridge/src/main/resources/application.properties`. Check that the `spring.kafka.bootstrap-servers` property is set to the correct address for your Kafka instance (e.g., `localhost:9092`).

3.  **Run the Service:**
    Navigate into the Java project's directory and run the application using the Maven wrapper.
    ```bash
    cd JavaBridge
    ./mvnw spring-boot:run
    ```

---

With both terminals running, the system is fully operational. The Java service will consume messages from Kafka and send them to the Python service for processing.

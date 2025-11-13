# k8s-observability-stack

A small project to explore the de-facto standard Kubernetes observability stack.

> **AI Disclaimer:** This project was developed with the assistance of Google's Gemini to guide the learning process, explain concepts, and generate configuration.

---

## Purpose

This project serves as a practical, hands-on sandbox for understanding the "three pillars" of observability (metrics, logs, and traces) in a modern cloud-native environment.

The goal is to build a complete, end-to-end stack on a local Kubernetes cluster using industry-standard open-source tools. It's a space to tinker with service instrumentation (OpenTelemetry), data collection (Prometheus, Loki, Tempo), and visualization (Grafana) to learn how these components connect.

---

## Core Technologies

This project builds a full observability stack using the following tools:

* **Cluster**: **`kind`** (Kubernetes in Docker) for a lightweight, declarative local cluster.
* **Deployment**: **`helmfile`** to manage and deploy all backend components and applications in a single, reproducible command.
* **Application Services**: Two **Python FastAPI** microservices (`api-gateway` and `user-service`).
* **Application Chart**: A local, generic **Helm Chart** (`/app-chart`) used to deploy both services.
* **Instrumentation**: **OpenTelemetry (OTel) SDK** instrumenting the Python apps to generate traces, metrics, and logs.
* **Collection**: **OTel Collector** deployed via Helm, configured to receive OTLP data and export it to all three backends.
* **Metrics**: **`kube-prometheus-stack`** which includes:
    * **Prometheus**: The de-facto standard for metrics collection.
    * **Alertmanager**: Handles alerts fired by Prometheus.
    * **Grafana**: The de-facto standard for visualization.
* **Logging**: **`loki`**, a lightweight, cost-effective log aggregation system.
* **Tracing**: **`tempo`**, a simple and scalable distributed tracing backend.
* **Repo Quality**: **`pre-commit`** hooks for linting YAML and scanning for secrets.

---

## Architecture

This project deploys a full observability stack where all components are connected.

```text
       [ Client ]
           |
       (Requests)
           |
    [ api-gateway ]--------------+
           |                     |
           v                     |
   [ user-service ]              |
           |                     |
           +---------------------+
                      |
           (Traces, Metrics, Logs)
                      |
                      v
             [ OTel Collector ]
                      |
         +------------+------------+
         |            |            |
    (Metrics)      (Traces)      (Logs)
         |            |            |
         v            v            v
   [ Prometheus ] [ Tempo ]     [ Loki ]
         ^            ^            ^
         |            |            |
         +------------+------------+
                      |
                  (Queries)
                      |
                 [ Grafana ]
```

### Component Overview

* **`api-gateway`**: The public-facing Python (FastAPI) service. It receives user requests, calls the `user-service`, and generates telemetry.
* **`user-service`**: An internal Python (FastAPI) service that simulates a database. It's called by the `api-gateway` and also generates telemetry.
* **`OTel Collector`**: A central agent that receives all telemetry (traces, metrics, logs) from the apps and exports it to the correct backends.
* **`Prometheus`**: The time-series database that stores all **metrics** (e.g., `api_user_requests_total`).
* **`Loki`**: The log aggregation system that stores all **logs** (e.g., `"Request received..."`).
* **`Tempo`**: The tracing backend that stores all **traces** (the end-to-end request spans).
* **`Grafana`**: The visualization UI (the "single pane of glass"). It queries Prometheus, Loki, and Tempo to build dashboards.

---

## How to Run Locally

This guide will get the entire stack, including the applications, running on your local machine.

### 1. Prerequisites

* **Docker Desktop**: Must be installed and running.
* **Homebrew**: Used for installing command-line tools on macOS.

### 2. Install Tools

Install all necessary command-line tools.

```bash
brew install kind kubectl helm helmfile pre-commit
brew install --cask docker # If you don't have Docker Desktop
```

**Highly Recommended:** `helmfile` requires the `helm-diff` plugin to run. Install it once with:
```bash
helm plugin install [https://github.com/databus23/helm-diff](https://github.com/databus23/helm-diff)
```

### 3. Clone and Set Up the Repository

```bash
git clone [https://github.com/YOUR_USERNAME/k8s-observability-stack.git](https://github.com/YOUR_USERNAME/k8s-observability-stack.git)
cd k8s-observability-stack
```
Install the Git pre-commit hooks:
```bash
pre-commit install
```

### 4. Start the Local Kubernetes Cluster

This command uses the `kind-config.yaml` to create the cluster and map ports to your `localhost`.

```bash
kind create cluster --name observability --config kind-config.yaml
```

### 5. Build and Load Application Images

You must build the service images and load them into the `kind` cluster *before* deploying.

```bash
# Build the images
docker build -t api-gateway:latest ./services/api-gateway
docker build -t user-service:latest ./services/user-service

# Load the images into the cluster
kind load docker-image api-gateway:latest --name observability
kind load docker-image user-service:latest --name observability
```

### 6. Deploy the Full Stack

This single command deploys all components: the backends (Prometheus, Loki, Tempo), the OTel Collector, and your two custom applications.

```bash
helmfile sync
```

### 7. Access the UIs

Once `helmfile sync` is complete, you can access the UIs:

* **Grafana**: **[http://localhost:3000](http://localhost:3000)**
    * **Login**: `admin` / `admin`
* **Prometheus**: **[http://localhost:9090](http://localhost:9090)**

### 8. Test the Application & See Results

1.  **Open a new terminal** and start a port-forward to the `api-gateway`:
    ```bash
    kubectl port-forward svc/api-gateway 8080:80
    ```
2.  **Open another terminal** and send requests:
    ```bash
    # Test a valid user
    curl http://localhost:8080/user/123

    # Test an invalid user (this will generate a 404 trace)
    curl http://localhost:8080/user/999
    ```
3.  **Go to Grafana**, open the **Explore** view (compass icon), and select the **Tempo** or **Loki** data source to see your traces and logs.

---

## How to Tear Down

You can destroy the entire setup with two commands:

1.  **Delete all Helm releases:**
    ```bash
    helmfile destroy
    ```
2.  **Delete the local cluster:**
    ```bash
    kind delete cluster --name observability
    ```

**To rebuild:** Run steps 4, 5, and 6 from the "How to Run Locally" section.

---

## Project Roadmap

* [x] **Step 1: Cluster Setup**
    * Configured a reproducible `kind` cluster.
* [x] **Step 2: Deploy Backends**
    * Used `helmfile` to deploy `kube-prometheus-stack`, `loki`, and `tempo`.
    * Configured Grafana data sources declaratively.
* [x] **Step 3: Repo Quality**
    * Added `pre-commit` hooks for YAML linting and secret scanning.
* [x] **Step 4: Build & Containerize App**
    * Created two Python FastAPI microservices (`api-gateway`, `user-service`).
    * Instrumented them with the OpenTelemetry (OTel) SDK for all three pillars.
    * Created `Dockerfiles` and built local images.
* [x] **Step 5: Deploy OTel Collector**
    * Deployed the OTel Collector via `helmfile`.
    * Configured it to receive OTLP and export to Prometheus, Loki, and Tempo.
* [x] **Step 6: Deploy App & Observe**
    * Created a local Helm chart (`app-chart`) to deploy the apps.
    * Deployed the apps via `helmfile`.
    * Generated traffic and confirmed all three pillars are visible in Grafana.

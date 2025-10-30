# k8s-observability-stack

A small project to explore the de-facto standard Kubernetes observability stack.

> **AI Disclaimer:** This project was developed with the assistance of Google's Gemini to guide the learning process, explain concepts, and generate configuration.

---

## Purpose

This project serves as a practical, hands-on sandbox for understanding the "three pillars" of observability (metrics, logs, and traces) in a modern cloud-native environment.

The goal is to build a complete, end-to-end stack on a local Kubernetes cluster using industry-standard open-source tools. It's a space to tinker with service instrumentation (OpenTelemetry), data collection (Prometheus, Loki), and visualization (Grafana) to learn how these components connect.

---

## Core Technologies

This project builds a full observability stack using the following tools:

* **Cluster**: **`kind`** (Kubernetes in Docker) for a lightweight, declarative local cluster.
* **Deployment**: **`helmfile`** to manage and deploy all backend components in a single, reproducible command.
* **Metrics**: **`kube-prometheus-stack`** which includes:
    * **Prometheus**: The de-facto standard for metrics collection and alerting.
    * **Grafana**: The de-facto standard for visualization ("the single pane of glass").
    * **Alertmanager**: Handles alerts fired by Prometheus.
* **Logging**: **`loki`**, a lightweight, cost-effective log aggregation system inspired by Prometheus.
* **Tracing**: **`tempo`**, Grafana's simple and scalable distributed tracing backend.
* **Instrumentation**: **OpenTelemetry (OTel)** (to be added) as the vendor-neutral standard for generating and exporting telemetry data from our applications.
* **Repo Quality**: **`pre-commit`** hooks for linting YAML and scanning for secrets.

---

## How to Run Locally

This guide will get the entire backend observability stack running on your local machine.

### 1. Prerequisites

* **Docker Desktop**: Must be installed and running. `kind` runs its cluster inside Docker.
* **Homebrew**: Used for installing command-line tools on macOS.

### 2. Install Tools

Install all necessary command-line tools using Homebrew:
```bash
brew install kind kubectl helm helmfile pre-commit
brew install --cask docker # If you don't have Docker Desktop
```

### 3. Clone and Set Up the Repository

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/YOUR_USERNAME/k8s-observability-stack.git](https://github.com/YOUR_USERNAME/k8s-observability-stack.git)
    cd k8s-observability-stack
    ```

2.  **Install the Git pre-commit hooks:**
    This activates the quality checks defined in `.pre-commit-config.yaml` (YAML linting, secret scanning, etc.).
    ```bash
    pre-commit install
    ```

### 4. Start the Local Kubernetes Cluster

This command uses the `kind-config.yaml` file to create a new cluster named `observability`. The config file also sets up port-forwarding from your `localhost` to the cluster for accessing the UIs.

```bash
kind create cluster --name observability --config kind-config.yaml
```

### 5. Deploy the Observability Backends

This single command reads the `helmfile.yaml` and deploys Prometheus, Grafana, Loki, and Tempo all at once.

```bash
helmfile sync
```
This will take a few minutes as it pulls the container images.

### 6. Access the UIs

Once `helmfile sync` is complete and the pods are running, you can access the services in your browser:

* **Grafana**: [http://localhost:3000](http://localhost:3000)
    * **Login**: `admin`
    * **Password**: `admin` (This is set in `helm-values/prometheus-values.yaml`)

* **Prometheus**: [http://localhost:9090](http://localhost:9090)

### Build and Load Application Images
After the backends are running, you must build the custom service images and load them into the `kind` cluster.

Run these commands from the root of the project to build and load the images into the cluster:

```bash
docker build -t api-gateway:latest ./services/api-gateway
docker build -t user-service:latest ./services/user-service

kind load docker-image api-gateway:latest --name observability
kind load docker-image user-service:latest --name observability
```

---

## How to Tear Down

You can easily destroy and re-create the entire setup.

1.  **Delete the backend services:**
    This will remove all the Helm charts from your cluster.
    ```bash
    helmfile destroy
    ```

2.  **Delete the local cluster:**
    This will delete the `kind` cluster and all its contents.
    ```bash
    kind delete cluster --name observability
    ```

To rebuild, just run `kind create ...` and `helmfile sync` again.

---

## Project Roadmap

This project is being built step-by-step.

* [x] **Step 1: Cluster Setup**
    * Configured a reproducible `kind` cluster.
    * Defined `extraPortMappings` to expose services.

* [x] **Step 2: Deploy Backends**
    * Used `helmfile` to create a declarative, reproducible installation.
    * Deployed `kube-prometheus-stack` (Prometheus, Grafana).
    * Deployed `loki` for logging.
    * Deployed `tempo` for tracing.

* [x] **Step 3: Repo Quality**
    * Added `pre-commit` hooks for YAML linting and secret scanning.

* [x] **Step 4: Build & Containerize App**
    * Create two simple microservices (e.g., Python/Go).
    * Instrument them with the OpenTelemetry (OTel) SDK.
    * Create `Dockerfiles` and build local images.

* [ ] **Step 5: Deploy OTel Collector**
    * Configure an OTel Collector to receive data from the apps.
    * Set up the collector's exporters to send metrics to Prometheus, logs to Loki, and traces to Tempo.

* [ ] **Step 6: Deploy App & Observe**
    * Deploy the instrumented microservices to the cluster.
    * Generate traffic and see the "three pillars" in Grafana.
    * Build a dashboard that correlates metrics, logs, and traces.
    * Set up an alert in Alertmanager.

# Architecture Overview

This diagram shows a high-level architecture overview of a typical cloud-native web application: CDN, load balancer, frontend, API gateway, microservices running in Kubernetes, databases, cache, message queue, observability, and CI/CD.

```mermaid
flowchart LR
  %% Users and edge
  A[User Browser / Mobile] -->|HTTP(S)| CDN[CDN / Edge Cache]
  CDN -->|TLS| WAF[WAF / Edge Security]
  WAF --> LB[Load Balancer]

  %% Frontend and static assets
  LB --> FE[Web Frontend (SPA)]
  FE -->|Static assets| S3[(Object Storage / CDN origin)]
  FE -->|API calls (REST/GraphQL / WebSocket)| API[API Gateway]

  %% Authentication
  API --> Auth[Auth Service (OAuth / JWT)]
  Auth --> DBAuth[(Auth DB)]

  %% Kubernetes cluster containing services
  subgraph K8s["Kubernetes Cluster"]
    direction TB
    Ingress[Ingress Controller] --> API
    API --> MSUser[User Service]
    API --> MSProduct[Product Service]
    API --> MSOrder[Order Service]
    API --> MSRealtime[Realtime / WebSocket Service]

    MSUser -->|cache read/write| Cache[(Redis Cache)]
    MSProduct --> Cache
    MSOrder --> MQ[(Message Broker)]
    MSOrder --> DB[(Primary SQL DB)]
    DB --> Replica[(Read Replica)]

    MQ -->|async events| MSProduct
    MSRealtime -->|pub/sub| MQ

    MSUser -->|metrics/logs| Observability
    MSProduct --> Observability
    MSOrder --> Observability
    MSRealtime --> Observability
  end

  %% Observability and operations
  Observability[Monitoring & Logging]
  Observability --> Prom[Prometheus & Grafana]
  Observability --> ELK[Logging / ELK or Loki]

  %% CI/CD and infra
  CI[CI/CD Pipeline]
  CI -->|Build / Test| Registry[Container Registry]
  CI -->|Deploy| K8s

  %% Backups and external services
  DB --> Backup[Backup Storage]
  S3 --> CDN

  %% Legend / notes (visual)
  classDef infra fill:#f8f9fa,stroke:#333,stroke-width:1px;
  class K8s,DB,S3,Cache,MQ,Registry,Backup infra;
```

Notes:
- This is a high-level diagram intended as a starting point. Replace service names and components to match your actual architecture.
- To preview: GitHub renders Mermaid diagrams in Markdown. Alternatively use VS Code + "Markdown Preview Mermaid Support" or https://mermaid.live.

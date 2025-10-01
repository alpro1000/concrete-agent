# TZDReader Architecture Diagrams

## Current Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        A[Client Request]
    end
    
    subgraph "API Layer"
        B[tzd_router.py<br/>FastAPI Router]
    end
    
    subgraph "Agent Layer"
        C[TZDReader Class<br/>__init__.py]
        D[tzd_reader Function<br/>agent.py]
        E[SecureAIAnalyzer<br/>agent.py]
        F[FileSecurityValidator<br/>security.py]
    end
    
    subgraph "Service Layer"
        G[DocParser<br/>File Parsing]
        H[MinerU<br/>PDF Extraction]
        I[LLM Service<br/>AI Processing]
    end
    
    subgraph "External Services"
        J[OpenAI API]
        K[Claude API]
        L[Perplexity API]
    end
    
    A --> B
    B --> C
    C --> D
    D --> F
    D --> G
    D --> H
    D --> E
    E --> I
    I --> J
    I --> K
    I --> L
    
    style A fill:#e1f5ff
    style B fill:#fff9c4
    style C fill:#c8e6c9
    style D fill:#c8e6c9
    style E fill:#c8e6c9
    style F fill:#c8e6c9
    style G fill:#ffccbc
    style H fill:#ffccbc
    style I fill:#ffccbc
    style J fill:#f8bbd0
    style K fill:#f8bbd0
    style L fill:#f8bbd0
```

## Improved Architecture (Recommended)

```mermaid
graph TB
    subgraph "Client Layer"
        A[Client Request]
    end
    
    subgraph "API Layer"
        B[tzd_router.py<br/>Endpoints Only]
        B1[Authentication<br/>Middleware]
        B2[Rate Limiting<br/>Middleware]
    end
    
    subgraph "Service Layer"
        S[TZDService<br/>Business Logic]
        S1[Validation Service]
        S2[Cache Service]
        S3[Monitoring Service]
    end
    
    subgraph "Agent Layer"
        C[TZDReader<br/>Public API]
        D[tzd_reader<br/>Core Logic]
        E[SecureAIAnalyzer<br/>AI Integration]
        F[FileSecurityValidator<br/>Security]
        G[Exception Handler<br/>Error Management]
    end
    
    subgraph "Infrastructure"
        H[DocParser<br/>Async]
        I[LLM Service<br/>with Retry]
        J[Prometheus<br/>Metrics]
        K[StructLog<br/>Logging]
    end
    
    subgraph "External"
        L[AI Providers]
        M[Monitoring System]
    end
    
    A --> B1
    B1 --> B2
    B2 --> B
    B --> S
    S --> S1
    S --> S2
    S1 --> C
    S2 -.cache hit.-> B
    C --> D
    D --> F
    D --> E
    D --> G
    E --> I
    I --> L
    F --> H
    D --> K
    D --> J
    J --> M
    K --> M
    
    style A fill:#e1f5ff
    style B fill:#fff9c4
    style B1 fill:#ffeb3b
    style B2 fill:#ffeb3b
    style S fill:#81c784
    style S1 fill:#a5d6a7
    style S2 fill:#a5d6a7
    style S3 fill:#a5d6a7
    style C fill:#4fc3f7
    style D fill:#4fc3f7
    style E fill:#4fc3f7
    style F fill:#4fc3f7
    style G fill:#4fc3f7
    style H fill:#ff8a65
    style I fill:#ff8a65
    style J fill:#ba68c8
    style K fill:#ba68c8
    style L fill:#f48fb1
    style M fill:#ce93d8
```

## Request Flow with Improvements

```mermaid
sequenceDiagram
    participant C as Client
    participant R as Router
    participant A as Auth
    participant RL as Rate Limiter
    participant S as TZDService
    participant Cache as Cache
    participant TZD as TZDReader
    participant LLM as LLM Service
    participant M as Monitoring
    
    C->>R: POST /analyze (files, engine)
    R->>A: Verify API Key
    A-->>R: ✓ Authorized
    R->>RL: Check Rate Limit
    RL-->>R: ✓ Within Limit
    R->>S: analyze_files(files, engine)
    S->>Cache: get(files, engine)
    
    alt Cache Hit
        Cache-->>S: Cached Result
        S-->>R: Return Result
        R-->>C: 200 OK (from cache)
    else Cache Miss
        Cache-->>S: None
        S->>TZD: analyze(files, engine)
        TZD->>M: Log: analysis_started
        TZD->>TZD: Validate Files
        TZD->>TZD: Parse Files (async)
        TZD->>LLM: analyze_text(text, provider)
        
        loop Retry on Failure
            LLM->>LLM: AI API Call
            alt Success
                LLM-->>TZD: Analysis Result
            else Temporary Error
                LLM->>LLM: Wait (exponential backoff)
            end
        end
        
        TZD->>M: Log: analysis_completed
        TZD->>M: Metrics: duration, success
        TZD-->>S: Analysis Result
        S->>Cache: set(files, engine, result)
        S-->>R: Return Result
        R-->>C: 200 OK
    end
    
    M->>M: Update Dashboards
```

## Error Handling Flow

```mermaid
graph TD
    A[Request Received] --> B{Validate Input}
    B -->|Invalid| C[ValidationError]
    B -->|Valid| D{Security Check}
    D -->|Failed| E[SecurityError]
    D -->|Passed| F{Parse Files}
    F -->|Empty Content| G[EmptyContentError]
    F -->|Success| H{AI Analysis}
    H -->|Rate Limit| I[RateLimitError]
    H -->|Timeout| J[TimeoutError]
    H -->|Temporary| K[TemporaryError]
    H -->|Success| L[Return Result]
    H -->|Permanent| M[AIServiceError]
    
    I -->|Retry| N{Attempts Left?}
    K -->|Retry| N
    J -->|Retry| N
    
    N -->|Yes| O[Wait with Backoff]
    N -->|No| P[Return Error]
    O --> H
    
    C --> Q[400 Bad Request]
    E --> Q
    G --> Q
    M --> R[500 Internal Error]
    P --> S{Error Type}
    S -->|Temporary| T[503 Service Unavailable]
    S -->|Permanent| R
    L --> U[200 OK]
    
    style A fill:#e1f5ff
    style L fill:#c8e6c9
    style U fill:#c8e6c9
    style C fill:#ffcdd2
    style E fill:#ffcdd2
    style G fill:#ffcdd2
    style I fill:#fff9c4
    style J fill:#fff9c4
    style K fill:#fff9c4
    style M fill:#ffcdd2
    style Q fill:#ff8a80
    style R fill:#ff8a80
    style T fill:#ffab91
```

## Monitoring Architecture

```mermaid
graph TB
    subgraph "TZDReader Agent"
        A[Application Code]
        B[StructLog Logger]
        C[Prometheus Metrics]
    end
    
    subgraph "Log Aggregation"
        D[Log Files<br/>JSON Format]
        E[Elasticsearch]
        F[Kibana Dashboard]
    end
    
    subgraph "Metrics Collection"
        G[Prometheus Server]
        H[Grafana Dashboard]
    end
    
    subgraph "Alerting"
        I[Alert Manager]
        J[Slack/Email]
    end
    
    A --> B
    A --> C
    B --> D
    D --> E
    E --> F
    C --> G
    G --> H
    G --> I
    I --> J
    
    style A fill:#4fc3f7
    style B fill:#ba68c8
    style C fill:#ba68c8
    style D fill:#fff9c4
    style E fill:#ffcc80
    style F fill:#a5d6a7
    style G fill:#ffcc80
    style H fill:#a5d6a7
    style I fill:#ff8a65
    style J fill:#f48fb1
```

## Performance Optimization Flow

```mermaid
graph LR
    A[Multiple Files] --> B{Use Cache?}
    B -->|Yes| C{Cache Hit?}
    C -->|Yes| D[Return Cached]
    C -->|No| E[Process Files]
    B -->|No| E
    
    E --> F[Parallel Processing]
    F --> G[File 1<br/>Process]
    F --> H[File 2<br/>Process]
    F --> I[File N<br/>Process]
    
    G --> J[Combine Results]
    H --> J
    I --> J
    
    J --> K{Cache Enabled?}
    K -->|Yes| L[Store in Cache]
    K -->|No| M[Return Result]
    L --> M
    
    D --> N[Add Cache Metadata]
    M --> O[Add Processing Metadata]
    
    N --> P[Final Response]
    O --> P
    
    style A fill:#e1f5ff
    style D fill:#c8e6c9
    style F fill:#fff9c4
    style G fill:#ffccbc
    style H fill:#ffccbc
    style I fill:#ffccbc
    style L fill:#ce93d8
    style P fill:#a5d6a7
```

## Deployment Architecture

```mermaid
graph TB
    subgraph "Load Balancer"
        LB[Nginx/Traefik]
    end
    
    subgraph "Application Instances"
        A1[TZDReader<br/>Instance 1]
        A2[TZDReader<br/>Instance 2]
        A3[TZDReader<br/>Instance N]
    end
    
    subgraph "Caching Layer"
        R[Redis Cache<br/>Shared]
    end
    
    subgraph "Monitoring Stack"
        P[Prometheus]
        G[Grafana]
        L[Loki/ELK]
    end
    
    subgraph "External Services"
        AI[AI Providers<br/>OpenAI/Claude]
    end
    
    LB --> A1
    LB --> A2
    LB --> A3
    
    A1 --> R
    A2 --> R
    A3 --> R
    
    A1 --> AI
    A2 --> AI
    A3 --> AI
    
    A1 --> P
    A2 --> P
    A3 --> P
    
    A1 --> L
    A2 --> L
    A3 --> L
    
    P --> G
    L --> G
    
    style LB fill:#ffeb3b
    style A1 fill:#4fc3f7
    style A2 fill:#4fc3f7
    style A3 fill:#4fc3f7
    style R fill:#ce93d8
    style P fill:#ff8a65
    style G fill:#a5d6a7
    style L fill:#ff8a65
    style AI fill:#f48fb1
```

## Legend

### Component Colors
- 🔵 **Blue** - Core Application Components
- 🟡 **Yellow** - API/Gateway Layer
- 🟢 **Green** - Business Logic/Services
- 🟣 **Purple** - Infrastructure (Logging, Metrics)
- 🟠 **Orange** - External Dependencies
- 🔴 **Red** - Errors/Alerts
- 🌸 **Pink** - Third-party Services

### Connection Types
- **Solid Line** (→) - Synchronous call
- **Dashed Line** (-->) - Asynchronous/Optional
- **Dotted Line** (...>) - Cache hit path

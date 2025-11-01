# ===========================================
# NexusERP AI - Prometheus Monitoring Configuration
# Complete observability stack
# ===========================================

global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'nexuserp-production'
    environment: 'production'

# Alertmanager configuration
alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - alertmanager:9093

# Load rules once and periodically evaluate them
rule_files:
  - "/etc/prometheus/rules/*.yml"

# Scrape configurations
scrape_configs:
  # ===========================================
  # Prometheus itself
  # ===========================================
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # ===========================================
  # Backend API
  # ===========================================
  - job_name: 'nexuserp-backend'
    metrics_path: '/metrics'
    static_configs:
      - targets: 
          - 'backend:8000'
    relabel_configs:
      - source_labels: [__address__]
        target_label: instance
        regex: '([^:]+)'

  # ===========================================
  # PostgreSQL Database
  # ===========================================
  - job_name: 'postgresql'
    static_configs:
      - targets: ['postgres-exporter:9187']

  # ===========================================
  # Redis Cache
  # ===========================================
  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']

  # ===========================================
  # Node Exporter (System Metrics)
  # ===========================================
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

  # ===========================================
  # NGINX
  # ===========================================
  - job_name: 'nginx'
    static_configs:
      - targets: ['nginx:8080']
    metrics_path: '/nginx_status'

  # ===========================================
  # Celery Workers
  # ===========================================
  - job_name: 'celery'
    static_configs:
      - targets: ['celery-exporter:9808']

  # ===========================================
  # Kubernetes Pods (Auto-discovery)
  # ===========================================
  - job_name: 'kubernetes-pods'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)
      - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
        action: replace
        regex: ([^:]+)(?::\d+)?;(\d+)
        replacement: $1:$2
        target_label: __address__

---
# ===========================================
# Alert Rules
# ===========================================
# Save as /etc/prometheus/rules/alerts.yml
groups:
  - name: nexuserp_alerts
    interval: 30s
    rules:
      # High CPU Usage
      - alert: HighCPUUsage
        expr: 100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage detected"
          description: "Instance {{ $labels.instance }} has CPU usage above 80% (current: {{ $value }}%)"

      # High Memory Usage
      - alert: HighMemoryUsage
        expr: (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100 > 85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage detected"
          description: "Instance {{ $labels.instance }} has memory usage above 85% (current: {{ $value }}%)"

      # Disk Space Low
      - alert: DiskSpaceLow
        expr: (node_filesystem_avail_bytes / node_filesystem_size_bytes) * 100 < 15
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Disk space running low"
          description: "Instance {{ $labels.instance }} has less than 15% disk space remaining (current: {{ $value }}%)"

      # Backend API Down
      - alert: BackendAPIDown
        expr: up{job="nexuserp-backend"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Backend API is down"
          description: "Backend API instance {{ $labels.instance }} has been down for more than 1 minute"

      # Database Connection Issues
      - alert: DatabaseConnectionIssues
        expr: up{job="postgresql"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Database connection issues"
          description: "PostgreSQL database {{ $labels.instance }} is unreachable"

      # High API Error Rate
      - alert: HighAPIErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) * 100 > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High API error rate detected"
          description: "Error rate is above 5% for {{ $labels.instance }} (current: {{ $value }}%)"

      # Slow API Response Time
      - alert: SlowAPIResponseTime
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Slow API response time"
          description: "95th percentile response time is above 1s (current: {{ $value }}s)"

      # Redis Connection Issues
      - alert: RedisConnectionIssues
        expr: up{job="redis"} == 0
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "Redis connection issues"
          description: "Redis instance {{ $labels.instance }} is unreachable"

      # Celery Queue Backlog
      - alert: CeleryQueueBacklog
        expr: celery_queue_length > 1000
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Celery queue backlog"
          description: "Celery queue has more than 1000 pending tasks"

      # Failed AI Agent Execution
      - alert: FailedAIAgentExecution
        expr: increase(ai_agent_failures_total[1h]) > 3
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Multiple AI agent execution failures"
          description: "AI agent {{ $labels.agent_type }} has failed {{ $value }} times in the last hour"

      # Low Inventory Alert
      - alert: LowInventoryAlert
        expr: inventory_low_stock_count > 10
        for: 30m
        labels:
          severity: info
        annotations:
          summary: "Multiple products low on stock"
          description: "{{ $value }} products are below reorder level"

      # High Customer Churn Rate
      - alert: HighCustomerChurnRate
        expr: rate(customer_churn_total[24h]) * 100 > 5
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "High customer churn rate detected"
          description: "Customer churn rate is {{ $value }}% (threshold: 5%)"

---
# ===========================================
# Grafana Dashboard Configuration (JSON)
# Save as grafana/dashboards/nexuserp-overview.json
# ===========================================
{
  "dashboard": {
    "title": "NexusERP AI - System Overview",
    "tags": ["nexuserp", "overview"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "API Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{ method }} {{ status }}"
          }
        ]
      },
      {
        "id": 2,
        "title": "API Response Time (p95)",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "id": 3,
        "title": "CPU Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "100 - (avg by (instance) (rate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100)",
            "legendFormat": "{{ instance }}"
          }
        ]
      },
      {
        "id": 4,
        "title": "Memory Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100",
            "legendFormat": "{{ instance }}"
          }
        ]
      },
      {
        "id": 5,
        "title": "Database Connections",
        "type": "graph",
        "targets": [
          {
            "expr": "pg_stat_database_numbackends",
            "legendFormat": "{{ datname }}"
          }
        ]
      },
      {
        "id": 6,
        "title": "Celery Queue Length",
        "type": "graph",
        "targets": [
          {
            "expr": "celery_queue_length",
            "legendFormat": "{{ queue }}"
          }
        ]
      },
      {
        "id": 7,
        "title": "AI Agent Executions",
        "type": "stat",
        "targets": [
          {
            "expr": "sum(increase(ai_agent_executions_total[24h]))",
            "legendFormat": "Total"
          }
        ]
      },
      {
        "id": 8,
        "title": "Active Users",
        "type": "stat",
        "targets": [
          {
            "expr": "active_users_total",
            "legendFormat": "Active"
          }
        ]
      }
    ]
  }
}

---
# ===========================================
# Docker Compose for Monitoring Stack
# Save as monitoring/docker-compose.yml
# ===========================================
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - ./rules:/etc/prometheus/rules
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'
    ports:
      - "9090:9090"
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./grafana/datasources:/etc/grafana/provisioning/datasources
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
      - GF_INSTALL_PLUGINS=redis-datasource
    ports:
      - "3001:3000"
    depends_on:
      - prometheus
    restart: unless-stopped

  alertmanager:
    image: prom/alertmanager:latest
    container_name: alertmanager
    volumes:
      - ./alertmanager.yml:/etc/alertmanager/alertmanager.yml
      - alertmanager_data:/alertmanager
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
      - '--storage.path=/alertmanager'
    ports:
      - "9093:9093"
    restart: unless-stopped

  node-exporter:
    image: prom/node-exporter:latest
    container_name: node-exporter
    command:
      - '--path.rootfs=/host'
    volumes:
      - /:/host:ro,rslave
    ports:
      - "9100:9100"
    restart: unless-stopped

  postgres-exporter:
    image: prometheuscommunity/postgres-exporter
    container_name: postgres-exporter
    environment:
      DATA_SOURCE_NAME: "postgresql://nexuserp:password@postgres:5432/nexuserp_db?sslmode=disable"
    ports:
      - "9187:9187"
    restart: unless-stopped

  redis-exporter:
    image: oliver006/redis_exporter
    container_name: redis-exporter
    environment:
      REDIS_ADDR: "redis:6379"
    ports:
      - "9121:9121"
    restart: unless-stopped

volumes:
  prometheus_data:
  grafana_data:
  alertmanager_data:

---
# ===========================================
# Alertmanager Configuration
# Save as monitoring/alertmanager.yml
# ===========================================
global:
  resolve_timeout: 5m
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'alerts@nexuserp.ai'
  smtp_auth_username: 'alerts@nexuserp.ai'
  smtp_auth_password: 'your-app-password'

route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'default'
  routes:
    - match:
        severity: critical
      receiver: 'critical-alerts'
    - match:
        severity: warning
      receiver: 'warning-alerts'

receivers:
  - name: 'default'
    email_configs:
      - to: 'team@nexuserp.ai'
        headers:
          Subject: 'NexusERP Alert: {{ .GroupLabels.alertname }}'

  - name: 'critical-alerts'
    email_configs:
      - to: 'oncall@nexuserp.ai'
        headers:
          Subject: '🚨 CRITICAL: {{ .GroupLabels.alertname }}'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
        channel: '#alerts-critical'
        title: '🚨 CRITICAL ALERT'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'

  - name: 'warning-alerts'
    email_configs:
      - to: 'team@nexuserp.ai'
        headers:
          Subject: '⚠️ WARNING: {{ .GroupLabels.alertname }}'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
        channel: '#alerts-warning'
        title: '⚠️ Warning Alert'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'

inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'instance']

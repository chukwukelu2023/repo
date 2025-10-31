# 📘 Nginx Failover & Error Monitoring Runbook

## 1. Service Overview and Context

This runbook outlines the procedures for operating and troubleshooting the **Nginx Failover & Error Monitoring System**.  
The system provides real-time visibility into the Nginx Blue/Green routing state and alerts on service degradation (high 5xx error rates).

| **Metric** | **Value** | **Notes** |
|-------------|------------|-----------|
| **Service Name** | monitor | Python application reading Nginx logs |
| **Repository Link** | [GitHub](https://github.com/chukwukelu2023/repo/blob/main/runbook.md) |  |
| **Location of Files** | `log_watcher/watcher.py` and `docker-compose.yml` |  |
| **Alert Channel** | `#monitor` | Slack channel receiving alerts |
| **Error Threshold** | `[2.0]%` | Configured via `ERROR_RATE_THRESHOLD` |
| **Key Upstreams** | app_blue (Primary), app_green (Backup) | The two application pools managed by Nginx |

---

## 2. Architecture and Data Flow

1. The system runs as a **sidecar container-monitor service**, sharing the Nginx volume where access logs are written.  
2. Nginx proxies requests to the active upstream (`blue` or `green`).  
3. Nginx writes request details (including `X-App-Pool` header) to the access log.  
4. The Python Monitor continuously reads the log file.  
5. The Monitor parses logs for:
   - **Status codes** (detecting 5xx)
   - **Upstream pool changes** (detecting failover)
6. If a critical condition is detected, the monitor sends an alert via **Slack Webhook**.

---

## 3. Key Health Checks

### 3.1 Nginx Routing Check

Determines which upstream is currently serving traffic.

| **Command** | **Expected Response** | **Healthy Status** |
|--------------|------------------------|--------------------|
| `curl http://<ip-addres>:8080/version` | HTTP 200 with `X-App-Pool: blue` | Blue pool active |
| `curl -I http://<ip-address>:8080/version` | HTTP 200 with `X-App-Pool: green` | Green pool active (Failover occurred) |

---

### 3.2 Service Health Check

Checks the internal health of application pools.

| **Pool** | **Command** | **Expected Outcome** |
|-----------|--------------|-----------------------|
| Blue | `curl http://<ip-address>:8081/version` | HTTP 200 |
| Green | `curl http://<ip>:8082/version` | HTTP 200 |

---

## 4. Incident Response & Troubleshooting

The following sections describe how to respond to Slack alerts.

---

### 🚨 Incident 1: Failover Detected (Blue → Green)

This alert means the **primary blue pool** is failing and Nginx has switched to the **green** backup.

| **Step** | **Action** | **Expected Resolution** |
|-----------|-------------|--------------------------|
| 1. Acknowledge | Post: `Acknowledged. Investigating blue pool health.` | Team is informed |
| 2. Check Blue Pool Health | Run: `curl http://<ip-address>:8081/version` | Confirms if blue app is still failing |
| 3. Investigate Logs | Check logs for blue pool. | Identify root cause |
| 4. Mitigate / Fix | Apply fix or restart the blue service. | Blue returns to HTTP 200 |
| 5. Monitor Switch Back | Wait for monitor to detect **Green → Blue** traffic switch. | Traffic returns to primary pool |

---

### 🚨 Incident 2: High 5xx Error Rate Exceeded

Indicates the active pool is returning excessive 5xx responses over a rolling window.

| **Step** | **Action** | **Decision / Next Step** |
|-----------|-------------|--------------------------|
| 1. Acknowledge | Post: `High error rate detected. Checking logs.` | Notify team and begin analysis |
| 2. Log Analysis | Check Nginx logs for failing endpoints and error codes. | Identify root cause (e.g., `/chaos/start`) |
| 3. Confirm Pool State | Run Routing Check | If still blue, issue persists; if green, failover may have started |
| 4. Trigger Chaos | Run: `curl -X POST 'http://<ip-address>:8081/chaos/start?mode=timeout'` | Forces failover to green pool |
| 5. Escalate | If issue persists. | May indicate shared system failure |

---

## 5. Routine Operations and Validation

Use these steps to validate system health or simulate incidents for testing.

---

### 5.1 System Startup and Health Check

| **Step** | **Command** | **Expected Result** |
|-----------|--------------|---------------------|
| 1. Start System | `docker compose up --build` | Nginx, app_blue, app_green, and monitor containers running |
| 2. Check Initial Route | `curl http://<ip-address>:8080/version` | HTTP 200 with `X-App-Pool: blue` |

---

### 5.2 Chaos Simulation: Forcing a Failover

| **Step** | **Command** | **Expected Monitor Alert** |
|-----------|--------------|-----------------------------|
| 1. Start Chaos | `curl -X POST 'http://<ip-address>:8081/chaos/start?mode=error'` | `Failover Detected: BLUE → GREEN` |
| 2. Verify Failover | `curl http://<ip-address>:8080/version` | `X-App-Pool: green` |
| 3. Stop Chaos | `curl -X POST 'http://<ip-address>:8081/chaos/stop'` | `Traffic Switch: GREEN → BLUE` |
| 4. Verify Switch Back | `curl http://<ip-address>:8080/version` | `X-App-Pool: blue` |

---

### 5.3 High Error Rate Simulation

| **Step** | **Command** | **Expected Monitor Alert** |
|-----------|--------------|-----------------------------|
| 1. Run Simulation | `./simulate.ps1 or .simulate.sh` | `High Error Rate Detected` alert sent |
| 2. Verify Cooldown | Continue running script | Alert suppressed during cooldown |
| 3. Stop Simulation | Stop the script | Error rate drops; no further alerts |

---

✅ **Tip:** Always confirm that both **Nginx** and the **log watcher** share the same volume path for `/logs/access.log`, otherwise no monitoring data will be captured.

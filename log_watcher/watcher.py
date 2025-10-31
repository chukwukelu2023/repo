import time
import os
import re
import requests
import logging
from collections import deque

LOG_FILE = os.getenv("NGINX_LOG_PATH")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
ERROR_RATE_THRESHOLD = float(os.getenv("ERROR_RATE_THRESHOLD", "2.0"))
WINDOW_SIZE = int(os.getenv("WINDOW_SIZE", "200"))
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "10"))
ALERT_COOLDOWN = float(os.getenv("ALERT_COOLDOWN", "300"))

# === LOGGING SETUP ===
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)

pattern = re.compile(
    r'(?P<ip>\S+) - - \[(?P<time>[^\]]+)\] "(?P<method>\S+) (?P<path>\S+) \S+" '
    r'status=(?P<status>\d+) [^ ]* pool=(?P<pool>\S+) release=(?P<release>\S+) '
    r'upstream_status=(?P<upstream_status>[0-9,\s]+) upstream_addr=(?P<upstream_addr>[0-9\.:,\s]+) '
    r'request_time=(?P<request_time>[\d\.]+) upstream_response_time=(?P<upstream_response_time>[\d\.,\s]+)'
)

# === GLOBAL STATE ===
recent = deque(maxlen=WINDOW_SIZE)
last_pool = os.getenv("ACTIVE_POOL", "blue")
last_check = 0.0
last_alert_time = {"failover": 0, "switch": 0, "error_rate": 0}


def send_slack_alert(message: str):
    if not SLACK_WEBHOOK_URL:
        logging.warning("SLACK_WEBHOOK_URL not set. Cannot send alert.")
        return
    try:
        response = requests.post(SLACK_WEBHOOK_URL, json={"text": message})
        response.raise_for_status()
        logging.info("Slack alert sent.")
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to send Slack alert: {e}")


# === ERROR RATE CHECK ===
def check_alert():
    now = time.time()

    while recent and now - recent[0][0] > WINDOW_SIZE * CHECK_INTERVAL:
        recent.popleft()

    total = len(recent)
    if total == 0:
        return

    errors = sum(1 for _, _, upstream_status in recent if upstream_status.startswith("5"))
    rate = (errors / total) * 100
    if rate >= ERROR_RATE_THRESHOLD and now - last_alert_time["error_rate"] > ALERT_COOLDOWN:
        last_alert_time["error_rate"] = now
        send_slack_alert(
            f"🚨 *High Error Rate Detected!*\n"
            f"• Error rate: `{rate:.2f}%`\n"
            f"• Error rate threshold: `{ERROR_RATE_THRESHOLD}%`\n"
            f"• Total requests: `{total}`\n"
            f"• Pool: `{last_pool}`\n"
            f"• Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}\n\n"
        )


def monitor_log():
    global last_pool, last_check
    logging.info("Starting log watcher...")
    send_slack_alert("👀 Log watcher started successfully and is monitoring Nginx logs.")

    while not os.path.exists(LOG_FILE):
        time.sleep(5)
    with open(LOG_FILE, "r") as f:
        f.seek(0, 2)
        while True:
            try:
                line = f.readline()
                if not line:
                    time.sleep(CHECK_INTERVAL)
                    continue

                match = pattern.search(line)
                logging.debug(f"Regex match: {match}")
                if not match:
                    continue

                data = match.groupdict()
                pool = data.get("pool")
                release = data.get("release")
                upstream_status = data.get("upstream_status")
                upstream = data.get("upstream_addr")
                status_list = [s.strip() for s in upstream_status.split(",")]
                addr_list = [a.strip() for a in upstream.split(",")]

                latest_status = status_list[-1] if status_list else upstream_status
                previous_status = status_list[0] if len(status_list) > 1 else status_list[0] if status_list else "N/A"

                previous_upstream = addr_list[0] if len(addr_list) > 1 else addr_list[0] if addr_list else "N/A"
                current_upstream = addr_list[-1] if addr_list else "N/A"
                logging.info(f"Parsed log line: pool={pool}, release={release}, upstream_status={upstream_status}, upstream={upstream}")
                # Track in recent deque
                recent.append((time.time(), pool, upstream_status))
                # Failover detection
                if upstream_status.startswith("5") and time.time() - last_alert_time["failover"] > ALERT_COOLDOWN:
                    last_alert_time["failover"] = time.time()
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                    send_slack_alert(
                        f"⚠️ *Failover Detected!*\n"
                        f"• Previous Pool: `{last_pool}`\n"
                        f"• New Pool: `{pool}`\n"
                        f"• Release: `{release}`\n"
                        f"• Previous Upstream: `{previous_upstream}`\n"
                        f"• Current Upstream: `{current_upstream}`\n"
                        f"• Previous Upstream Status: `{previous_status}`\n"
                        f"• Current Upstream Status: `{latest_status}`\n"
                        f"• Time: {timestamp}\n\n"
                    )
                    logging.warning(f"Failover detected from {last_pool} → {pool} ({release})")

                # Traffic switch detection
                elif pool != last_pool and time.time() - last_alert_time["switch"] > ALERT_COOLDOWN:
                    last_alert_time["switch"] = time.time()
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                    send_slack_alert(
                        f"🔄 *Traffic Switch Detected!*\n"
                        f"• Switched from `{last_pool}` → `{pool}`\n"
                        f"• Release: `{release}`\n"
                        f"• Upstream: `{upstream}`\n"
                        f"• Upstream Status: `{latest_status}`\n"
                        f"• Time: {timestamp}\n\n"
                    )
                    logging.info(f"Traffic switch detected: {last_pool} → {pool}")

                last_pool = pool

                if time.time() - last_check >= CHECK_INTERVAL:
                        check_alert()
                        last_check = time.time()

            except Exception as e:
                logging.error(f"Error processing log line: {e}")
                time.sleep(2)



if __name__ == "__main__":
    try:
        monitor_log()
    except KeyboardInterrupt:
        send_slack_alert("🛑 Log monitor stopped manually by user.")
        logging.info("Log watcher stopped manually.")
    except Exception as e:
        send_slack_alert(f"❌ Log monitor stopped due to error: `{e}`")
        logging.error(f"Log watcher stopped due to error: {e}")

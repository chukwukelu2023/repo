#!/bin/bash
# ==========================
# Chaos Simulation Script
# ==========================

BASE_NGINX="http://localhost:8080/version"
CHAOS_ON="http://localhost:8081/chaos/start?mode=error"
CHAOS_OFF="http://localhost:8081/chaos/stop"
TOTAL_REQUESTS=120
TOGGLE_INTERVAL=3  # Toggle error every 3 requests
IN_ERROR_MODE=false

echo "🚀 Starting Chaos Simulation..."
echo "Sending $TOTAL_REQUESTS requests to $BASE_NGINX with chaos toggled every $TOGGLE_INTERVAL requests"
echo ""

for ((i=1; i<=TOTAL_REQUESTS; i++)); do
  # Toggle chaos mode every N requests
  if (( i % TOGGLE_INTERVAL == 0 )); then
    if [ "$IN_ERROR_MODE" = true ]; then
      echo -e "\n[$i] 🟢 Turning OFF error mode on Blue..."
      if curl -s -X POST "$CHAOS_OFF" > /dev/null; then
        IN_ERROR_MODE=false
      else
        echo "Failed to stop chaos."
      fi
    else
      echo -e "\n[$i] 🔴 Turning ON error mode on Blue..."
      if curl -s -X POST "$CHAOS_ON" > /dev/null; then
        IN_ERROR_MODE=true
      else
        echo "Failed to start chaos."
      fi
    fi
  fi

  # Send request to Nginx (load balancer)
  HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_NGINX")
  if [[ "$HTTP_STATUS" == "200" ]]; then
    echo "[$i] ✅ Status: $HTTP_STATUS"
  else
    echo "[$i] ❌ Error: $HTTP_STATUS"
  fi

  # Sleep 0.1 second
  sleep 0.1
done

# Ensure chaos mode is turned off at the end
echo -e "\n🧹 Stopping any remaining chaos mode..."
curl -s -X POST "$CHAOS_OFF" > /dev/null || echo "Cleanup failed."

echo -e "\n✅ Simulation complete!"

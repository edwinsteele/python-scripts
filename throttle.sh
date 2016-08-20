#!/bin/sh

# Throttles heavy uploaders that are affecting upstream throughput

# Immediate upstream PPP endpoint
UPSTREAM_IP=$(netstat -rn | awk '$8 ~ /pppoe0/ && $3 ~ /UGS/ {print $2};')
PING_COUNT=5
PACKET_COUNT=100
PING_THRESHOLD_MS=20
#PING_THRESHOLD_MS=500

# Source Pushover token and user
. $HOME/.profile_private

function send_pushover_notification {
  pushover_status=$(curl -s \
    --form-string "token=$WORDSPEAK_PUSHOVER_API_TOKEN" \
    --form-string "user=$WORDSPEAK_PUSHOVER_USER" \
    --form-string "message=$pushover_message" \
    https://api.pushover.net/1/messages.json | jq '.status')
}

# Average round trip as an integer
avg_round_trip_ms=$(ping -q -c $PING_COUNT $UPSTREAM_IP | grep round-trip | cut -d'/' -f5 | cut -d"." -f1)

if [ $avg_round_trip_ms -gt $PING_THRESHOLD_MS ]; then
  # Work out who's sledging the line, dob on them
  # Look on the internal interface - which assumes that there won't be any
  #  internal traffic of consequence going through the firewall. That's currently
  #  the case.
  start_time_secs=$(date +%s)
  echo "$(date): Ping to $UPSTREAM_IP too slow: ($avg_round_trip_ms ms). Displaying top talkers:"
  # Capture inbound packets, but ignore acks. This shows us non-trivial upstream activity
  #  which is usually what cripples the line
  #top_talkers=$(doas tcpdump -D in -c $PACKET_COUNT -r /tmp/gem0-20160820061728.pcap -n 'tcp[tcpflags] != tcp-ack and not dst net 192.168.20/24' 2>/dev/null |
  top_talkers=$(doas tcpdump -D in -c $PACKET_COUNT -i gem0 -n 'tcp[tcpflags] != tcp-ack and not dst net 192.168.20/24' 2>/dev/null |
    sed 's/^[0-9:\.]* \([0-9]*\.[0-9]*\.[0-9]*\.[0-9]*\)[0-9 \.]*> \([0-9\.]*\):.*/\1 -> \2/' |
    sort |
    uniq -c |
    sort -nr |
    head -5)
  echo "$top_talkers"
  end_time_secs=$(date +%s)
  echo "$(date): Capture time of $(( $end_time_secs-$start_time_secs )) secs"
  top_talker_dest=$(echo "$top_talkers" | head -1 | awk '{print $4;}' | cut -d"." -f1-4)
  top_talker_port=$(echo "$top_talkers" | head -1 | awk '{print $4;}' | cut -d"." -f5)
  top_talker_src=$(echo "$top_talkers" | head -1 | awk '{print $2;}')
  echo "Adding top talker IP, $top_talker_dest, to low-priority-outbound-traffic table. Table follows:"
  doas pfctl -q -t low-priority-outbound-traffic -T add $top_talker_dest
  doas pfctl -t low-priority-outbound-traffic -T show
  # Give some time for the network to settle before sending a message
  #  given we need to use the network to send.
  sleep 10
  pushover_message="Throttled top talker $(dig +short -x $top_talker_dest) ($top_talker_dest:$top_talker_port) from $(dig +short -x $top_talker_src)"
  send_pushover_notification
  if [ "$pushover_status" -eq "1" ]; then
    echo "Pushover message sent successfully"
  else
    echo "Pushover message failed - status: $pushover_status"
  fi
else
  echo "$(date): Ping to $UPSTREAM_IP ok: ($avg_round_trip_ms ms)."
fi

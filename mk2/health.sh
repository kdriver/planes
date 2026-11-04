#!/usr/bin/env bash
# pi-health.sh — health check for a Raspberry Pi (with extra checks for PiAware)
#
# Usage:   ./pi-health.sh        full report
#          ./pi-health.sh -q     quiet: only show warnings and problems
#
# Exit code: 0 = all OK, 1 = warnings, 2 = something critical
# (handy if you run it from cron or another script)

set -u

# ---- Thresholds (tweak to taste) -------------------------------------------
TEMP_WARN=70;  TEMP_CRIT=80      # CPU temperature, °C (Pi throttles at ~80-85)
DISK_WARN=80;  DISK_CRIT=90      # % of disk used
INODE_WARN=80; INODE_CRIT=90     # % of inodes used
MEM_WARN=85;   MEM_CRIT=95       # % of RAM in use (based on MemAvailable)
SWAP_RATE_WARN=100               # swap activity, pages/sec in+out (100 ≈ 400 KB/s)
SWAP_RATE_CRIT=1000              # (1000 ≈ 4 MB/s — the Pi will feel sluggish)
SWAP_SAMPLE_SECS=5               # how long to watch swap activity
SWAP_FULL_WARN=90; SWAP_FULL_CRIT=98  # % of swap used — only matters near the top
LOAD_WARN=1.0; LOAD_CRIT=2.0     # 5-minute load average *per CPU core*
FEED_STALE_SECS=60               # PiAware: receiver data older than this = stuck
PING_HOST=1.1.1.1                # used to test internet connectivity
DNS_HOST=flightaware.com         # used to test name resolution

# ---- Output helpers ---------------------------------------------------------
QUIET=0
[[ "${1:-}" == "-q" ]] && QUIET=1

if [[ -t 1 ]]; then
  G=$'\e[32m'; Y=$'\e[33m'; R=$'\e[31m'; B=$'\e[1m'; N=$'\e[0m'
else
  G=; Y=; R=; B=; N=
fi

STATUS=0; WARNS=0; CRITS=0
ok()      { (( QUIET )) || printf '  %s[ OK ]%s %s\n' "$G" "$N" "$1"; }
warn()    { printf '  %s[WARN]%s %s\n' "$Y" "$N" "$1"; WARNS=$((WARNS+1)); (( STATUS < 1 )) && STATUS=1; }
crit()    { printf '  %s[CRIT]%s %s\n' "$R" "$N" "$1"; CRITS=$((CRITS+1)); STATUS=2; }
section() { (( QUIET )) || printf '\n%s%s%s\n' "$B" "$1" "$N"; }

# check VALUE WARN CRIT MESSAGE — works with decimals
check() {
  local v=$1 w=$2 c=$3 msg=$4
  if   awk -v v="$v" -v c="$c" 'BEGIN{exit !(v>=c)}'; then crit "$msg"
  elif awk -v v="$v" -v w="$w" 'BEGIN{exit !(v>=w)}'; then warn "$msg"
  else ok "$msg"
  fi
}

join() { local IFS=", "; echo "$*"; }

# ---- System info ------------------------------------------------------------
if (( ! QUIET )); then
  model=$(tr -d '\0' 2>/dev/null < /proc/device-tree/model || echo "Unknown model")
  printf '%sPi health check — %s%s\n' "$B" "$(hostname)" "$N"
  printf '  %s | kernel %s | %s\n' "$model" "$(uname -r)" "$(uptime -p)"
  printf '  Checked %s\n' "$(date '+%a %d %b %Y %H:%M:%S')"
fi

# ---- Temperature & power ----------------------------------------------------
section "Temperature & power"

if [[ -r /sys/class/thermal/thermal_zone0/temp ]]; then
  temp=$(awk '{printf "%.1f", $1/1000}' /sys/class/thermal/thermal_zone0/temp)
  check "$temp" "$TEMP_WARN" "$TEMP_CRIT" "CPU temperature ${temp}°C"
else
  warn "Couldn't read CPU temperature"
fi

if command -v vcgencmd >/dev/null 2>&1 && thr=$(vcgencmd get_throttled 2>/dev/null); then
  thr=${thr#*=}
  t=$((thr))
  now=(); past=()
  (( t & 0x1 ))     && now+=("under-voltage")
  (( t & 0x2 ))     && now+=("CPU frequency capped")
  (( t & 0x4 ))     && now+=("throttled")
  (( t & 0x8 ))     && now+=("soft temperature limit")
  (( t & 0x10000 )) && past+=("under-voltage")
  (( t & 0x20000 )) && past+=("CPU frequency capped")
  (( t & 0x40000 )) && past+=("throttled")
  (( t & 0x80000 )) && past+=("soft temperature limit")
  if (( ${#now[@]} )); then
    crit "Happening now: $(join "${now[@]}") ($thr) — check power supply and cooling"
  elif (( ${#past[@]} )); then
    warn "Has happened since boot: $(join "${past[@]}") ($thr) — power supply or cooling may be marginal"
  else
    ok "No under-voltage or throttling since boot"
  fi
else
  warn "Couldn't run vcgencmd to check power/throttling (is your user in the 'video' group?)"
fi

# ---- CPU load ---------------------------------------------------------------
section "CPU"

cores=$(nproc)
read -r l1 l5 l15 _ < /proc/loadavg
per_core=$(awk -v l="$l5" -v c="$cores" 'BEGIN{printf "%.2f", l/c}')
check "$per_core" "$LOAD_WARN" "$LOAD_CRIT" \
  "Load average $l1 / $l5 / $l15 (1/5/15 min) on $cores cores — ${per_core} per core"

top_proc=$(ps -eo comm,%cpu --sort=-%cpu --no-headers 2>/dev/null | head -1 | awk '{print $1" ("$2"% CPU)"}')
[[ -n "$top_proc" ]] && (( ! QUIET )) && printf '         Busiest process: %s\n' "$top_proc"

# ---- Memory -----------------------------------------------------------------
section "Memory"

read -r mt ma st sf < <(awk '
  /^MemTotal:/{t=$2} /^MemAvailable:/{a=$2} /^SwapTotal:/{st=$2} /^SwapFree:/{sf=$2}
  END{print t, a, st, sf}' /proc/meminfo)

mem_used=$(( (mt - ma) * 100 / mt ))
check "$mem_used" "$MEM_WARN" "$MEM_CRIT" \
  "RAM ${mem_used}% in use — $((ma / 1024)) MB available of $((mt / 1024)) MB"

if (( st > 0 )); then
  # How much is actually moving in/out of swap right now? That's what signals
  # memory pressure — idle data parked in swap is normal and harmless.
  swap_io() { awk '/^pswpin /{i=$2} /^pswpout /{o=$2} END{print i+o}' /proc/vmstat; }
  s1=$(swap_io); sleep "$SWAP_SAMPLE_SECS"; s2=$(swap_io)
  rate=$(( (s2 - s1) / SWAP_SAMPLE_SECS ))
  check "$rate" "$SWAP_RATE_WARN" "$SWAP_RATE_CRIT" \
    "Swap activity ${rate} pages/sec over ${SWAP_SAMPLE_SECS}s (0 = idle)"

  # Fullness: only a concern when swap is close to running out
  swap_used=$(( (st - sf) * 100 / st ))
  check "$swap_used" "$SWAP_FULL_WARN" "$SWAP_FULL_CRIT" \
    "Swap ${swap_used}% full — $(((st - sf) / 1024)) MB of $((st / 1024)) MB"
else
  ok "No swap configured"
fi

# ---- Storage ----------------------------------------------------------------
section "Storage"

while read -r _ _ _ avail pct mnt; do
  p=${pct%\%}
  [[ "$p" =~ ^[0-9]+$ ]] || continue
  check "$p" "$DISK_WARN" "$DISK_CRIT" "Disk $mnt ${pct} used ($avail free)"
done < <(df -hP -x tmpfs -x devtmpfs -x squashfs -x overlay 2>/dev/null | tail -n +2)

while read -r _ _ _ _ pct mnt; do
  p=${pct%\%}
  [[ "$p" =~ ^[0-9]+$ ]] || continue
  (( p >= INODE_WARN )) && check "$p" "$INODE_WARN" "$INODE_CRIT" "Inodes on $mnt ${pct} used (too many small files)"
done < <(df -iP -x tmpfs -x devtmpfs -x squashfs -x overlay 2>/dev/null | tail -n +2)

root_opts=$(awk '$2=="/"{print $4}' /proc/mounts | tail -1)
if [[ ",$root_opts," == *",ro,"* ]]; then
  crit "Root filesystem is mounted read-only — often a sign the SD card is failing"
else
  ok "Root filesystem is writable"
fi

if command -v journalctl >/dev/null 2>&1; then
  io_errs=$(journalctl -k -b --no-pager -q 2>/dev/null \
            | grep -Eic 'mmc.*(error|timeout)|I/O error|EXT4-fs error|Buffer I/O' || true)
  if (( io_errs > 0 )); then
    warn "$io_errs storage/SD card error(s) in the kernel log since boot — back up and consider a new card"
  else
    ok "No storage errors in the kernel log since boot"
  fi
fi

# ---- Services ---------------------------------------------------------------
section "Services"

failed=$(systemctl --failed --no-legend --plain 2>/dev/null | awk '{print $1}')
if [[ -n "$failed" ]]; then
  crit "Failed systemd units: $(join $failed)"
else
  ok "No failed systemd services"
fi

# PiAware-related services: only checked if installed and enabled
for svc in piaware dump1090-fa dump978-fa readsb; do
  enabled=$(systemctl is-enabled "$svc" 2>/dev/null || true)
  [[ "$enabled" == "enabled" ]] || continue
  if systemctl is-active --quiet "$svc"; then
    ok "$svc is running"
  else
    crit "$svc is enabled but not running (try: sudo systemctl restart $svc)"
  fi
done

# Is the ADS-B receiver actually producing data?
for f in /run/dump1090-fa/aircraft.json /run/readsb/aircraft.json; do
  [[ -r "$f" ]] || continue
  age=$(( $(date +%s) - $(stat -c %Y "$f") ))
  n=$(grep -o '"hex"' "$f" | wc -l)
  if (( age > FEED_STALE_SECS )); then
    crit "Receiver data is ${age}s old — the decoder or SDR dongle may be stuck"
  elif (( n == 0 )); then
    warn "Receiver is running but seeing 0 aircraft — check the antenna and dongle"
  else
    ok "Receiver data is fresh — currently seeing $n aircraft"
  fi
  break
done

# ---- Network ----------------------------------------------------------------
section "Network"

if ping -c1 -W3 "$PING_HOST" >/dev/null 2>&1; then
  ok "Internet reachable (ping $PING_HOST)"
else
  crit "Can't reach the internet (ping $PING_HOST failed)"
fi

if getent hosts "$DNS_HOST" >/dev/null 2>&1; then
  ok "DNS working (resolved $DNS_HOST)"
else
  crit "DNS lookup for $DNS_HOST failed"
fi

# ---- Summary ----------------------------------------------------------------
echo
case $STATUS in
  0) printf '%s%sAll checks passed — the Pi looks healthy.%s\n' "$B" "$G" "$N" ;;
  1) printf '%s%s%d warning(s) — worth a look, nothing urgent.%s\n' "$B" "$Y" "$WARNS" "$N" ;;
  2) printf '%s%s%d critical issue(s), %d warning(s) — needs attention.%s\n' "$B" "$R" "$CRITS" "$WARNS" "$N" ;;
esac

exit $STATUS

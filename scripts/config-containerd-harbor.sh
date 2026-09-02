#!/usr/bin/env bash
set -euo pipefail

REGISTRY="${1:-10.1.106.200:8088}"
CERTS_DIR="/etc/containerd/certs.d/${REGISTRY}"
CONFIG_FILE="/etc/containerd/config.toml"

mkdir -p "${CERTS_DIR}"

cat >"${CERTS_DIR}/hosts.toml" <<EOF
server = "http://${REGISTRY}"

[host."http://${REGISTRY}"]
  capabilities = ["pull", "resolve", "push"]
  skip_verify = true
EOF

cp "${CONFIG_FILE}" "${CONFIG_FILE}.bak.$(date +%Y%m%d%H%M%S)"

python3 - <<'PY'
from pathlib import Path

path = Path("/etc/containerd/config.toml")
text = path.read_text()
text = text.replace("config_path = ''", "config_path = '/etc/containerd/certs.d'")
path.write_text(text)
PY

systemctl restart containerd
sleep 5

crictl pull "${REGISTRY}/devops-demo/date-service:1.0.0"

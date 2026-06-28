#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

for script in 01-orchestration 02-async-workflow 03-knowledge-acquisition 04-observability; do
  echo ""
  echo "########################################################"
  echo "# $script"
  echo "########################################################"
  bash "$DIR/$script.sh"
done

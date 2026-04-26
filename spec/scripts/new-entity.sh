#!/usr/bin/env bash
# Scaffold a new stateful entity: append a stub to round-1/entities.json
# and create round-2/<id>-state-machine.json with the canonical layout.
#
# Usage:
#   bash scripts/new-entity.sh E.RESERVATION Reservation "PENDING CONFIRMED CANCELLED"
#
# Args:
#   $1  entity ID (e.g. E.RESERVATION)
#   $2  entity name (e.g. Reservation)
#   $3  space-separated state list (e.g. "PENDING CONFIRMED CANCELLED")

set -euo pipefail

if [ $# -lt 3 ]; then
    echo "Usage: $0 <ENTITY_ID> <NAME> '<STATE_1> <STATE_2> ...'"
    exit 2
fi

ID="$1"
NAME="$2"
STATES="$3"
SM="spec/round-2/${ID}-state-machine.json"

if [ -e "$SM" ]; then
    echo "ERROR: $SM already exists. Refusing to overwrite."
    exit 1
fi

# Build states JSON array
states_json="["
first=1
for s in $STATES; do
    if [ $first -eq 1 ]; then first=0; else states_json+=","; fi
    states_json+="\"$s\""
done
states_json+="]"

cat > "$SM" <<EOF
{
  "\$schema": "../.ci/schemas/state-machine.schema.json",
  "entity": "$ID",
  "states": $states_json,
  "events": [],
  "cells": []
}
EOF

echo "Created $SM"
echo "Next:"
echo "  1. Add the entity record to spec/round-1/entities.json (id=$ID, name=$NAME)."
echo "  2. Add events to the matrix above."
echo "  3. Dispatch the round-2 agent to fill cells (see agents/round-2-state-event.md)."

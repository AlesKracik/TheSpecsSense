#!/usr/bin/env bash
# Scaffold a new stateful entity:
#   * round-2/<ID>.qnt           — Quint state machine (authoritative)
#   * round-2/<ID>-notes.json    — JSON companion (per-cell _note, evidence, rationale)
#
# Usage:
#   bash scripts/new-entity.sh E.RESERVATION Reservation "PENDING CONFIRMED CANCELLED"
#
# Args:
#   $1  entity ID (e.g. E.RESERVATION)
#   $2  entity name (e.g. Reservation) — used as the Quint module name
#   $3  space-separated state list (e.g. "PENDING CONFIRMED CANCELLED"). The first
#       state is treated as the initial state.

set -euo pipefail

if [ $# -lt 3 ]; then
    echo "Usage: $0 <ENTITY_ID> <NAME> '<STATE_1> <STATE_2> ...'"
    exit 2
fi

ID="$1"
NAME="$2"
STATES="$3"

QNT="spec/round-2/${ID}.qnt"
NOTES="spec/round-2/${ID}-notes.json"

if [ -e "$QNT" ]; then
    echo "ERROR: $QNT already exists. Refusing to overwrite."
    exit 1
fi
if [ -e "$NOTES" ]; then
    echo "ERROR: $NOTES already exists. Refusing to overwrite."
    exit 1
fi

# Build the Quint `type State = A | B | C` body and the JSON states array.
type_body=""
states_json="["
first=1
initial_state=""
for s in $STATES; do
    if [ -z "$initial_state" ]; then initial_state="$s"; fi
    if [ $first -eq 1 ]; then
        type_body="$s"
        states_json+="\"$s\""
        first=0
    else
        type_body="$type_body | $s"
        states_json+=",\"$s\""
    fi
done
states_json+="]"

cat > "$QNT" <<EOF
// Round 2 state machine for ${ID} (${NAME}).
//
// Authoritative for states, events, and per-event handler actions.
// The companion file ${ID}-notes.json carries _note, evidence, rationale,
// and justification_ref — every field Quint cannot enforce.
//
// Round 5's invariants.qnt imports this module and adds val predicates over
// it; Round 5 does not add var/type/action declarations here.

module ${NAME} {

  type State = ${type_body}

  var s: State

  action init = all {
    s' = ${initial_state}
  }

  // Add one \`action handle_<event_name> = ...\` per declared event in
  // ${ID}-notes.json. Each body is a guarded \`any { ... }\` over the
  // applicable (state, event) cells.

  action step = any {
    // any { handle_<event_1>, handle_<event_2>, ... }
    all { false }
  }
}
EOF

cat > "$NOTES" <<EOF
{
  "\$schema": "../.ci/schemas/state-machine.schema.json",
  "entity": "$ID",
  "states": $states_json,
  "events": [],
  "cells": []
}
EOF

echo "Created $QNT"
echo "Created $NOTES"
echo "Next:"
echo "  1. Add the entity record to spec/round-1/entities.json (id=$ID, name=$NAME)."
echo "  2. Add events to the notes file's \"events\" array AND a matching"
echo "     \`action handle_<event_name>\` in the .qnt; wire it into \`step\`."
echo "  3. Dispatch the round-2 agent to fill cells (see agents/round-2-state-event.md)."

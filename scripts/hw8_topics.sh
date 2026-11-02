#!/bin/sh
set -eu
for specification in entity_requests:1 entity_responses:1 inbox:1 tasks:2 drafts:1 final:1 dead_letter:1; do
  topic="s0686_${specification%:*}"
  partitions="${specification#*:}"
  docker compose -f compose.hw08.yml exec -T kafka /opt/kafka/bin/kafka-topics.sh \
    --bootstrap-server kafka:19092 --create --if-not-exists --topic "$topic" \
    --partitions "$partitions" --replication-factor 1
done
docker compose -f compose.hw08.yml exec -T kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka:19092 --describe --topic 's0686_.*'

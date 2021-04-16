#!/bin/bash
for task in "$@"; do {
  $task &
} done
echo "Procesos terminados"

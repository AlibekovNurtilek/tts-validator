#!/bin/bash

ports=(8081)

for port in "${ports[@]}"; do
    pid=$(lsof -ti :$port)  # Get PID of the process using the port
    if [ -n "$pid" ]; then
        echo "Killing process on port $port (PID: $pid)..."
        kill -9 $pid
    else
        echo "No process running on port $port."
    fi
done


#!/bin/bash
# pre-release plugin for fluentd async - fixes hanging container bug
# See issue: https://github.com/moby/moby/issues/40063

echo "installing docker plugin: async-fluentd-logger (pre-release)"
docker plugin install \
    --alias fluentd-async \
    akerouanton/fluentd-async-logger:v0.3
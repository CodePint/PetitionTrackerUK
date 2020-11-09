#!/bin/bash
# pre-release plguin for fluentd async, fixes hanging container bug
# See issue: https://github.com/moby/moby/issues/40063

echo installing docker plugin: async-fluentd-logger (pre-relase)
docker plugin install \
    --alias fluentd-async \
    aakerouanton/fluentd-async-logger:v0.3
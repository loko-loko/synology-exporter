#!/bin/bash

CONFIG_FILE="/exporter/config.yml"

[ ! -e $CONFIG_PATH ] && { echo "<!> Config file needed: $CONFIG_PATH"; exit 1; }

# Run exporter with args
/usr/local/bin/synology-exporter --config $CONFIG_FILE $@


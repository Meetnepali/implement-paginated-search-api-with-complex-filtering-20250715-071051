#!/bin/sh
set -e
apt-get update
apt-get install -y --no-install-recommends python3 python3-pip
pip3 install fastapi uvicorn

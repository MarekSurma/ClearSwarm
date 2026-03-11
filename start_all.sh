#!/bin/bash

# Load nvm
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

# Start frontend with Node 22
nvm use 22 && make frontend-dev &

# Start backend
./start_web.sh

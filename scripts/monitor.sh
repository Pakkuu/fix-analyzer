#!/bin/bash
tail -n 0 -f /home/ubuntu/fix-analyzer/logs/fix-session.log \
    | python3 /home/ubuntu/fix-analyzer/parser/parser.py

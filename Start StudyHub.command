#!/bin/zsh
# Double-click to start StudyHub with progress saving (keep this window open while you study).
cd "$(dirname "$0")"
(sleep 1; open "http://localhost:8000/") &
python3 serve.py

#!/bin/bash
# tmux 세션에서 Home Agent 봇 실행
SESSION="home-agent"

if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "이미 실행 중입니다. 접속: tmux attach -t $SESSION"
    exit 1
fi

cd /home/seongmin-choi/home-agent
tmux new-session -d -s "$SESSION" \
    "set -a && source .env && set +a && unset CLAUDECODE && ./venv/bin/python -m bot.main; echo '--- 종료됨. 아무 키나 누르세요 ---'; read"

echo "Home Agent 시작됨. 접속: tmux attach -t $SESSION"

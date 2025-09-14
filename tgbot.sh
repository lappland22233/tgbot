#!/bin/bash

# 检查并激活虚拟环境
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动机器人
python bot.py
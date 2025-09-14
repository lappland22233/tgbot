# Telegram 个人管理机器人
**tgbot** 是一个基于 [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) 和AI开发的 Telegram 个人管理机器人。
## 功能列表

1. **管理员系统**
   - `/rbq <用户ID>` - 添加管理员
   - `/rbq` - 显示管理员列表
   - `/unrbq <编号>` - 删除管理员

2. **群组授权管理**
   - `/sq` - 授权当前群组
   - `/unsq` - 取消授权

3. **提示词管理**
   - `/addmpt <提示词>` - 添加提示词
   - `/mpt <编号>` - 切换提示词
   - `/mpt` - 显示提示词列表
   - `/unmpt <编号>` - 删除提示词

4. **其他功能**
   - `/addke <关键词> <回复>` - 添加关键词回复
   - `/mll <模型名称>` - 切换AI模型

## 安装与运行

1. 安装依赖:
```bash
pip install -r requirements.txt
```

2. 首次运行配置:
```bash
python bot.py
```

3. 使用启动脚本:
```bash
./tgbot.sh
```

## 系统要求
- Python 3.8+
- Debian 12+/Ubuntu 22+
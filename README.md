# Telegram 个人AI聊天机器人
**tgbot** 是一个基于 [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) 和AI开发的 Telegram 个人使用AI聊天机器人。
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
   - `/addke <关键词> ` - 添加关键词检测并回复
   - `/mll <模型名称>` - 临时切换AI模型重启失效（默认是qwen-plus需要永久切换请到ai_service.py里面第12行的self.current_model = "填写模型名称"模型列表请前往阿里云官网查看）
   - `/boom <秒数>` - 设置bot消息自动删除 0为不删除
     
## 准备工作与运行
#准备工作
1.有一个能连接Telegram的电脑/服务器，如果需要24*7小时不间断运行推荐使用[AKILEcloud](https://akile.io/register?aff_code=f26ab36b-ff75-4ed4-82cc-cb5d5b81ec6a)的服务器，低价并且可靠性高。

2.前往[阿里百炼大模型](https://dashi.aliyun.com/activity/ydsbl?userCode=1bdcekfy&clubBiz=subTask..12101003..10239..)注册并领取免费百万免费Token然后获取大模型APi密钥

3.前往telegram的[@BotFather](https://t.me/@BotFather)获取bot密钥和[@userinfobot](https://t.me/@userinfobot)获取你的用户ID
 
#运行

1.克隆整个仓库并且给予tgbot.sh可执行权限

2. 使用启动脚本:
```bash
./tgbot.sh
```
3.根据要求填入对应密钥

## 系统要求
- Python 3.8+

import os
import logging
import datetime
import asyncio
from typing import List, Any

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# 依赖外部模块：Config, DataManager, AIService
from config import Config
from data_manager import DataManager
from ai_service import AIService


# 确保日志目录存在并初始化日志
log_dir = os.path.expanduser("~/log")
os.makedirs(log_dir, exist_ok=True)
logfile = os.path.join(log_dir, f"bot-{datetime.datetime.now().strftime('%Y-%m-%d')}.log")

logging.basicConfig(
    filename=logfile,
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TelegramBot:
    def __init__(self):
        self.config = Config()
        self.data_manager = DataManager()
        self.ai_service = AIService()

        # 本地保存一份当前模型 / 提示词状态
        self.current_model = getattr(self.ai_service, 'current_model', 'qwen-plus')
        self.current_prompt = "You are a helpful assistant."

        # 默认不删除消息
        self.boom_time = 0

        # Telegram 应用
        self.app = Application.builder().token(self.config.telegram_token).build()

        # 注册命令与消息处理
        self._register_handlers()

    # ---- DataManager 安全封装 ----
    def _safe_load(self, attr_name: str, default: Any = None):
        default = [] if default is None else default
        file_attr = getattr(self.data_manager, attr_name, None)
        if not file_attr:
            return default
        try:
            return self.data_manager.load_data(file_attr) or default
        except Exception as e:
            logger.exception("加载 %s 失败: %s", file_attr, e)
            return default

    def _safe_save(self, attr_name: str, data: Any) -> bool:
        file_attr = getattr(self.data_manager, attr_name, None)
        if not file_attr:
            logger.error("DataManager 未提供 %s 属性，保存失败", attr_name)
            return False
        try:
            self.data_manager.save_data(file_attr, data)
            return True
        except Exception as e:
            logger.exception("保存 %s 失败: %s", file_attr, e)
            return False

    # ---- 注册 handlers ----
    def _register_handlers(self):
        self.app.add_handler(CommandHandler("rbq", self.add_admin))
        self.app.add_handler(CommandHandler("unrbq", self.remove_admin))

        self.app.add_handler(CommandHandler("sq", self.authorize_group))
        self.app.add_handler(CommandHandler("unsq", self.deauthorize_group))

        self.app.add_handler(CommandHandler("addmpt", self.add_prompt))
        self.app.add_handler(CommandHandler("mpt", self.manage_prompt))
        self.app.add_handler(CommandHandler("unmpt", self.remove_prompt))

        self.app.add_handler(CommandHandler("addke", self.add_keyword))
        self.app.add_handler(CommandHandler("ke", self.list_keywords))
        self.app.add_handler(CommandHandler("unke", self.remove_keyword))
        self.app.add_handler(CommandHandler("mll", self.manage_model))
        self.app.add_handler(CommandHandler("boom", self.set_boom_time))  # 新增命令
     
        self.app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), self.handle_message))

     # ---- 工具方法 ----
    async def _reply(self, update: Update, text: str):
        try:
            sent_msg = None
            if update and update.message:
                sent_msg = await update.message.reply_text(text)
            elif update and update.effective_chat:
                sent_msg = await self.app.bot.send_message(chat_id=update.effective_chat.id, text=text)

            # 如果设置了 boom_time，在后台异步删除消息，不阻塞主流程
            if sent_msg and self.boom_time > 0:
                # 创建一个后台任务来处理删除操作
                asyncio.create_task(self._delayed_delete(sent_msg, self.boom_time))

        except Exception as e:
            logger.exception("发送消息失败: %s", e)
            
    async def _delayed_delete(self, message, delay_seconds: int):
        """在后台异步删除消息，不阻塞主流程"""
        try:
            await asyncio.sleep(delay_seconds)
            await message.delete()
        except Exception as e:
            logger.warning("删除消息失败: %s", e)

    def _is_supergroup_or_group(self, update: Update) -> bool:
        t = getattr(update.effective_chat, 'type', '')
        return t in ("group", "supergroup")
    # ---- 命令实现 ----
# ---- /boom 命令实现 ----
    async def set_boom_time(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """设置消息自毁时间"""
        try:
            if not context.args:
                await self._reply(update, f"当前自毁时间: {self.boom_time} 秒 (0=不删除)")
                return

            try:
                seconds = int(context.args[0])
            except ValueError:
                await self._reply(update, "❌ 参数无效，请输入数字秒数")
                return

            if seconds < 0:
                await self._reply(update, "❌ 秒数不能小于0")
                return

            self.boom_time = seconds
            if seconds == 0:
                await self._reply(update, "✅ 已设置: 消息不自动删除")
            else:
                await self._reply(update, f"✅ 已设置: 消息将在 {seconds} 秒后删除")
        except Exception as e:
            logger.exception("set_boom_time 出现异常: %s", e)
            await self._reply(update, "❌ 内部错误，查看日志了解详情")
            
    # ---- /rbq 命令实现 ----
    async def add_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            user_id = update.effective_user.id
            if user_id != self.config.admin_id:
                await self._reply(update, "❌ 只有主管理员可以添加管理员")
                return

            if not context.args:
                await self._reply(update, "用法: /rbq <用户ID>")
                return

            try:
                new_admin = int(context.args[0])
            except ValueError:
                await self._reply(update, "❌ 无效的用户ID：需要整数")
                return

            admins = self._safe_load('admin_file', [])
            # 统一存成 int
            admins = [int(a) for a in admins]
            if new_admin in admins:
                await self._reply(update, "⚠️ 该用户已是管理员")
                return

            admins.append(new_admin)
            if self._safe_save('admin_file', admins):
                await self._reply(update, f"✅ 已添加管理员 {new_admin}")
            else:
                await self._reply(update, "❌ 添加管理员失败（保存出错）")
        except Exception as e:
            logger.exception("add_admin 出现异常: %s", e)
            await self._reply(update, "❌ 内部错误，查看日志了解详情")

    async def remove_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            user_id = update.effective_user.id
            if user_id != self.config.admin_id:
                await self._reply(update, "❌ 只有主管理员可以移除管理员")
                return

            admins = self._safe_load('admin_file', [])
            if not context.args:
                # 显示管理员列表
                if not admins:
                    await self._reply(update, "管理员列表为空")
                    return
                msg = "管理员列表:\n" + "\n".join(f"{i+1}. {admin}" for i, admin in enumerate(admins))
                await self._reply(update, msg)
                return

            key = context.args[0]
            # 支持：编号（从1开始）或直接传用户ID
            try:
                maybe = int(key)
            except ValueError:
                await self._reply(update, "❌ 无效的编号或用户ID")
                return

            # 如果输入的数字在 1..len 则认为是编号；否则尝试作为用户ID移除
            if 1 <= maybe <= len(admins):
                index = maybe - 1
                removed = admins.pop(index)
                if self._safe_save('admin_file', admins):
                    await self._reply(update, f"✅ 已移除管理员 {removed}")
                else:
                    await self._reply(update, "❌ 移除失败（保存出错）")
                return

            # 否则按用户ID移除（保持与 admins 元素类型一致）
            try:
                admins_int = [int(a) for a in admins]
                if maybe in admins_int:
                    admins_int.remove(maybe)
                    if self._safe_save('admin_file', admins_int):
                        await self._reply(update, f"✅ 已移除管理员 {maybe}")
                    else:
                        await self._reply(update, "❌ 移除失败（保存出错）")
                else:
                    await self._reply(update, "❌ 未找到该管理员")
            except Exception:
                await self._reply(update, "❌ 无法处理管理员列表的类型")

        except Exception as e:
            logger.exception("remove_admin 出现异常: %s", e)
            await self._reply(update, "❌ 内部错误，查看日志了解详情")

    async def authorize_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            if not self._is_supergroup_or_group(update):
                await self._reply(update, "❌ 此命令只能在群组中使用")
                return

            group_id = update.effective_chat.id
            groups = self._safe_load('group_file', [])
            groups = [int(g) for g in groups]
            if group_id not in groups:
                groups.append(group_id)
                if self._safe_save('group_file', groups):
                    await self._reply(update, "✅ 群组已授权")
                else:
                    await self._reply(update, "❌ 群组授权失败（保存出错）")
            else:
                await self._reply(update, "⚠️ 群组已授权")
        except Exception as e:
            logger.exception("authorize_group 出现异常: %s", e)
            await self._reply(update, "❌ 内部错误，查看日志了解详情")

    async def deauthorize_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            if not self._is_supergroup_or_group(update):
                await self._reply(update, "❌ 此命令只能在群组中使用")
                return

            group_id = update.effective_chat.id
            groups = self._safe_load('group_file', [])
            groups = [int(g) for g in groups]
            if group_id in groups:
                groups.remove(group_id)
                if self._safe_save('group_file', groups):
                    await self._reply(update, "✅ 群组已取消授权")
                else:
                    await self._reply(update, "❌ 取消授权失败（保存出错）")
            else:
                await self._reply(update, "⚠️ 群组未被授权")
        except Exception as e:
            logger.exception("deauthorize_group 出现异常: %s", e)
            await self._reply(update, "❌ 内部错误，查看日志了解详情")

    async def add_prompt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            if not context.args:
                await self._reply(update, "用法: /addmpt <提示词>")
                return
            prompt = " ".join(context.args).strip()
            if not prompt:
                await self._reply(update, "❌ 提示词为空")
                return

            prompts = self._safe_load('prompt_file', [])
            prompts.append(prompt)
            if self._safe_save('prompt_file', prompts):
                await self._reply(update, f"✅ 已添加提示词 #{len(prompts)}")
            else:
                await self._reply(update, "❌ 添加提示词失败（保存出错）")
        except Exception as e:
            logger.exception("add_prompt 出现异常: %s", e)
            await self._reply(update, "❌ 内部错误，查看日志了解详情")

    async def manage_prompt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            prompts = self._safe_load('prompt_file', [])
            if not context.args:
                if not prompts:
                    await self._reply(update, "当前没有可用的提示词")
                    return
                msg = "可用提示词:\n" + "\n".join(
                    f"{i+1}. {p if len(p) <= 50 else p[:47] + '...'}" for i, p in enumerate(prompts)
                )
                await self._reply(update, msg)
                return

            # 切换提示词
            try:
                index = int(context.args[0]) - 1
            except ValueError:
                await self._reply(update, "❌ 无效的编号")
                return

            if 0 <= index < len(prompts):
                self.current_prompt = prompts[index]
                await self._reply(update, f"✅ 已切换至提示词 #{index+1}")
            else:
                await self._reply(update, "❌ 无效的编号")
        except Exception as e:
            logger.exception("manage_prompt 出现异常: %s", e)
            await self._reply(update, "❌ 内部错误，查看日志了解详情")

    async def remove_prompt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            if not context.args:
                await self._reply(update, "用法: /unmpt <编号>")
                return

            try:
                index = int(context.args[0]) - 1
            except ValueError:
                await self._reply(update, "❌ 无效的编号")
                return

            prompts = self._safe_load('prompt_file', [])
            if 0 <= index < len(prompts):
                removed = prompts.pop(index)
                if self._safe_save('prompt_file', prompts):
                    await self._reply(update, f"✅ 已删除提示词: {removed[:50]}...")
                else:
                    await self._reply(update, "❌ 删除提示词失败（保存出错）")
            else:
                await self._reply(update, "❌ 无效的编号")
        except Exception as e:
            logger.exception("remove_prompt 出现异常: %s", e)
            await self._reply(update, "❌ 内部错误，查看日志了解详情")

    async def manage_model(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            if not context.args:
                await self._reply(update, f"当前模型: {self.current_model}")
                return
            model = " ".join(context.args).strip()
            if not model:
                await self._reply(update, "❌ 模型名为空")
                return

            # 更新本地状态与 AI 服务（如果支持）
            self.current_model = model
            try:
                if hasattr(self.ai_service, 'set_model'):
                    self.ai_service.set_model(model)
            except Exception:
                logger.exception("切换模型时 ai_service.set_model 报错")

            await self._reply(update, f"✅ 已切换至模型: {model}")
        except Exception as e:
            logger.exception("manage_model 出现异常: %s", e)
            await self._reply(update, "❌ 内部错误，查看日志了解详情")

    async def list_keywords(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """展示关键词列表"""
        try:
            if hasattr(self.data_manager, 'get_keywords'):
                keywords = self.data_manager.get_keywords()
            else:
                keywords = self._safe_load('keyword_file', [])
            
            if not keywords:
                await self._reply(update, "当前没有关键词")
                return
                
            msg = "关键词列表:\n" + "\n".join(
                f"{i+1}. {item['keyword'] if isinstance(item, dict) else item}"
                for i, item in enumerate(keywords)
            )
            await self._reply(update, msg)
        except Exception as e:
            logger.exception("list_keywords 出现异常: %s", e)
            await self._reply(update, "❌ 内部错误，查看日志了解详情")

    async def remove_keyword(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """删除关键词"""
        try:
            if not context.args:
                await self._reply(update, "用法: /unke <编号>")
                return

            try:
                index = int(context.args[0]) - 1
            except ValueError:
                await self._reply(update, "❌ 无效的编号")
                return

            if hasattr(self.data_manager, 'remove_keyword'):
                try:
                    if self.data_manager.remove_keyword(index):
                        await self._reply(update, f"✅ 已删除关键词 #{index+1}")
                    else:
                        await self._reply(update, "❌ 删除失败")
                    return
                except Exception:
                    logger.exception("data_manager.remove_keyword 调用失败，切换到手动保存方式")

            # 手动处理
            keywords = self._safe_load('keyword_file', [])
            if 0 <= index < len(keywords):
                removed = keywords.pop(index)
                removed_key = removed['keyword'] if isinstance(removed, dict) else removed
                if self._safe_save('keyword_file', keywords):
                    await self._reply(update, f"✅ 已删除关键词: {removed_key}")
                else:
                    await self._reply(update, "❌ 删除关键词失败（保存出错）")
            else:
                await self._reply(update, "❌ 无效的编号")
        except Exception as e:
            logger.exception("remove_keyword 出现异常: %s", e)
            await self._reply(update, "❌ 内部错误，查看日志了解详情")

    async def add_keyword(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            if not context.args:
                await self._reply(update, "用法: /addke <关键词>")
                return

            keyword = " ".join(context.args).strip()
            if not keyword:
                await self._reply(update, "❌ 关键词为空")
                return

            # 如果 DataManager 提供 add_keyword 优化接口则使用，否则用文件保存
            if hasattr(self.data_manager, 'add_keyword'):
                try:
                    self.data_manager.add_keyword(keyword, None)  # 回复内容设为None
                    await self._reply(update, f"✅ 已添加关键词: {keyword}")
                    return
                except Exception:
                    logger.exception("data_manager.add_keyword 调用失败，切换到手动保存方式")

            # 手动保存到 keyword_file（期望格式: list of dicts [{'keyword':..., 'response':None}, ...])
            keywords = self._safe_load('keyword_file', [])
            keywords.append({'keyword': keyword, 'response': None})  # 回复内容设为None
            if self._safe_save('keyword_file', keywords):
                await self._reply(update, f"✅ 已添加关键词: {keyword}")
            else:
                await self._reply(update, "❌ 添加关键词失败（保存出错）")
        except Exception as e:
            logger.exception("add_keyword 出现异常: %s", e)
            await self._reply(update, "❌ 内部错误，查看日志了解详情")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            # 防止没有消息对象或是机器人发送的消息
            if not update.message or update.effective_user is None:
                return
            if getattr(update.effective_user, 'is_bot', False):
                return

            message_text = (update.message.text or "").strip()
            if not message_text:
                return

            # ---- 检查是否 at bot 或 回复 bot ----
            bot_username = (await self.app.bot.get_me()).username
            is_at_bot = bot_username and (f"@{bot_username.lower()}" in message_text.lower())
            
            # 精确判断是否是回复给当前机器人的消息
            is_reply_to_bot = False
            if (update.message.reply_to_message 
                and update.message.reply_to_message.from_user
                and update.message.reply_to_message.from_user.is_bot
                and hasattr(update.message.reply_to_message.from_user, 'id')):
                # 确保回复的是当前机器人，而不是其他机器人
                reply_bot_id = update.message.reply_to_message.from_user.id
                current_bot_id = (await self.app.bot.get_me()).id
                is_reply_to_bot = (reply_bot_id == current_bot_id)

            # ---- 检查关键词触发 ----
            keywords = []
            if hasattr(self.data_manager, 'get_keywords'):
                try:
                    keywords = self.data_manager.get_keywords()
                except Exception:
                    logger.exception("data_manager.get_keywords 调用失败，尝试从文件加载")
                    keywords = self._safe_load('keyword_file', [])
            else:
                keywords = self._safe_load('keyword_file', [])

            matched_keywords = []
            for item in keywords:
                k = item.get('keyword') if isinstance(item, dict) else item
                if not k:
                    continue
                if k.lower() in message_text.lower():
                    matched_keywords.append(k)

            # 如果没有关键词匹配，且不是 at bot 或回复 bot，就直接返回
            if not (matched_keywords or is_at_bot or is_reply_to_bot):
                return

            # 记录匹配的关键词
            if matched_keywords:
                logger.info(f"消息匹配到关键词: {', '.join(matched_keywords)}")

            # 群组授权检查
            if self._is_supergroup_or_group(update):
                groups = [int(g) for g in self._safe_load('group_file', [])]
                if update.effective_chat.id not in groups:
                    # 未授权群组不处理消息
                    return
                    
            # 再次确认是否满足回复条件（防止在授权检查后逻辑错误）
            if not (matched_keywords or is_at_bot or is_reply_to_bot):
                return
                
            # 调用 AI 服务
            user_name = update.effective_user.full_name if update.effective_user else 'user'
            try:
                response_text = await self.ai_service.chat_completion(
                    messages=[
                        {'role': 'system', 'content': self.current_prompt},
                        {'role': 'user', 'content': message_text}
                    ],
                    user_name=user_name,
                )
                # 确保 response_text 是字符串，不是 None
                if response_text is None:
                    response_text = "AI 服务返回了空响应"
            except Exception:
                logger.exception("ai_service.chat_completion 调用失败")
                response_text = "抱歉，AI 服务暂时不可用。"

            # 用统一的 _reply 发送（支持 /boom 自毁）
            await self._reply(update, response_text)

        except Exception as e:
            logger.exception("handle_message 出现异常: %s", e)

    def run(self):
        logger.info("Bot starting...")
        self.app.run_polling()


if __name__ == '__main__':
    bot = TelegramBot()
    bot.run()

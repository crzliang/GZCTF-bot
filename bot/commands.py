"""
命令处理模块
"""
from nonebot import on_command, on_regex
from nonebot.adapters.onebot.v11 import Bot, Event
import re
from .config import TARGET_GAME_ID
from .database import get_game_title, get_game_rankings, get_game_info
from .utils import (
    format_ranking_message,
    format_game_info_message,
    validate_command_prerequisites, 
    send_response, 
    log_command_result, 
    log_database_error,
    check_admin_permission
)
from .notifications import set_auto_broadcast_enabled, is_auto_broadcast_enabled


# 定义命令触发（使用正则严格匹配，避免 /rankabc 触发 /rank）
rank = on_regex(r'^/rank$', priority=5)
game_command = on_regex(r'^/game$', priority=5)
help_command = on_regex(r'^/help$', priority=5)
# 自动播报控制命令
open_broadcast = on_regex(r'^/open$', priority=5)
close_broadcast = on_regex(r'^/close$', priority=5)
# 使用正则表达式匹配 rank-xx 格式的命令（仅两位数字）
# rank_prefix = on_regex(r'^/rank-(\d{2})$', priority=4)
# 匹配所有以 / 开头的未知命令（优先级设置为较低，确保其他命令先匹配）
unknown_command = on_regex(r'^/', priority=99)


@rank.handle()
async def handle_rank(bot: Bot, event: Event):
    """处理排行榜查询命令"""
    # 验证先决条件
    error_msg = await validate_command_prerequisites("rank", event)
    if error_msg:
        if error_msg == "PERMISSION_DENIED":
            return  # 静默处理权限拒绝
        await rank.finish(error_msg)

    try:
        # 获取赛事标题
        game_title = await get_game_title(int(TARGET_GAME_ID))
        
        # 获取排行榜数据
        ranking_data = await get_game_rankings(int(TARGET_GAME_ID))
        log_command_result("rank", int(TARGET_GAME_ID), len(ranking_data), "teams")
        
        if not ranking_data:
            await rank.finish(f"比赛 '{game_title}' 暂无排行榜数据。")
        
        # 格式化并发送消息
        text = format_ranking_message(game_title, ranking_data)
        await send_response(bot, event, text, "rank")
        
    except Exception as e:
        log_database_error("rank", e)
        await rank.finish("查询排行榜失败！")


@game_command.handle()
async def handle_game(bot: Bot, event: Event):
    """处理比赛信息查询命令"""
    # 验证先决条件
    error_msg = await validate_command_prerequisites("game", event)
    if error_msg:
        if error_msg == "PERMISSION_DENIED":
            return  # 静默处理权限拒绝
        await game_command.finish(error_msg)

    try:
        # 获取比赛信息
        game_info = await get_game_info(int(TARGET_GAME_ID))
        log_command_result("game", int(TARGET_GAME_ID), 1, "game info")
        
        # 格式化并发送消息
        text = format_game_info_message(game_info)
        await send_response(bot, event, text, "game")
        
    except Exception as e:
        log_database_error("game", e)
        await game_command.finish("查询比赛信息失败！")


@help_command.handle()
async def handle_help(bot: Bot, event: Event):
    """处理帮助命令"""
    # 只需要权限检查，不需要数据库配置
    error_msg = await validate_command_prerequisites("help", event)
    if error_msg == "PERMISSION_DENIED":
        return  # 静默处理权限拒绝

    help_text = """
帮助文档
帮助文档

可用命令：
• /help - 显示此帮助信息
• /rank - 查看排行榜
• /game - 查看比赛信息
    """.strip()
    
    try:
        await send_response(bot, event, help_text, "help")
    except Exception as e:
        log_database_error("help", e)


@open_broadcast.handle()
async def handle_open_broadcast(bot: Bot, event: Event):
    """开启自动播报"""
    # 检查管理员权限
    if not check_admin_permission(event):
        await send_response(bot, event, "权限不足，只有管理员才能执行此命令。", "open")
        return
    
    # 只做权限检查
    error_msg = await validate_command_prerequisites("open", event)
    if error_msg:
        if error_msg == "PERMISSION_DENIED":
            return
        await open_broadcast.finish(error_msg)
    
    try:
        if is_auto_broadcast_enabled():
            await send_response(bot, event, "自动播报已是开启状态。", "open")
            return
        set_auto_broadcast_enabled(True)
        await send_response(bot, event, "已开启自动播报。", "open")
    except Exception as e:
        log_database_error("open", e)


@close_broadcast.handle()
async def handle_close_broadcast(bot: Bot, event: Event):
    """关闭自动播报"""
    # 检查管理员权限
    if not check_admin_permission(event):
        await send_response(bot, event, "权限不足，只有管理员才能执行此命令。", "close")
        return
    
    # 只做权限检查
    error_msg = await validate_command_prerequisites("close", event)
    if error_msg:
        if error_msg == "PERMISSION_DENIED":
            return
        await close_broadcast.finish(error_msg)
    
    try:
        if not is_auto_broadcast_enabled():
            await send_response(bot, event, "自动播报已是关闭状态。", "close")
            return
        set_auto_broadcast_enabled(False)
        await send_response(bot, event, "已关闭自动播报。", "close")
    except Exception as e:
        log_database_error("close", e)


@unknown_command.handle()
async def handle_unknown_command(bot: Bot, event: Event):
    """处理未知命令"""
    # 获取消息内容
    message_text = str(event.get_message()).strip()
    
    # 已知命令列表（严格匹配）
    known_commands = ['/rank', '/game', '/help', '/open', '/close']
    
    # 检查是否严格匹配已知命令（只允许命令本身，不允许后面带其他字符）
    if message_text in known_commands:
        return
    
    # 权限检查
    error_msg = await validate_command_prerequisites("unknown", event)
    if error_msg == "PERMISSION_DENIED":
        return  # 静默处理权限拒绝
    
    await send_response(bot, event, "何意味～", "unknown")


# @rank_prefix.handle()
# async def handle_rank_prefix(bot: Bot, event: Event):
#     """处理带学号前缀的排行榜查询，如 /rank-25"""
#     # 验证先决条件
#     error_msg = await validate_command_prerequisites("rank-prefix", event)
#     if error_msg:
#         if error_msg == "PERMISSION_DENIED":
#             return  # 静默处理权限拒绝
#         await rank_prefix.finish(error_msg)
#
#     # 从消息中提取学号前缀
#     message_text = str(event.get_message()).strip()
#     match = re.search(r'/rank-(\d{2})', message_text)
#     if not match:
#         await rank_prefix.finish("请使用正确格式，例如：/rank-25")
#         return
#
#     prefix_str = match.group(1)
#
#     try:
#         # 获取赛事标题
#         game_title = await get_game_title(int(TARGET_GAME_ID))
#
#         # 获取按学号前缀过滤的排行榜数据
#         ranking_data = await get_game_rankings_by_stdnum_prefix(int(TARGET_GAME_ID), prefix_str)
#         log_command_result("rank-prefix", int(TARGET_GAME_ID), len(ranking_data), f"teams (prefix={prefix_str})")
#
#         if not ranking_data:
#             await rank_prefix.finish(f"'{game_title}' 赛事中未找到{prefix_str}级的队伍。")
#
#         # 格式化并发送消息，标题包含前缀信息
#         text = format_ranking_message(f"{game_title} - {prefix_str} 级", ranking_data)
#         await send_response(bot, event, text, "rank-prefix")
#
#     except Exception as e:
#         log_database_error("rank-prefix", e)
#         await rank_prefix.finish("查询排行榜失败！")

"""
命令处理模块
"""
from nonebot import on_regex
from nonebot.adapters.onebot.v11 import Bot, Event
import httpx
from .config import GZCTF_BASE_URL, TARGET_GAME_ID
from .utils import (
    validate_command_prerequisites,
    send_response,
    log_database_error,
    check_admin_permission
)
from .notifications import set_auto_broadcast_enabled, is_auto_broadcast_enabled


# 排行榜查询命令
rank = on_regex(r'^/rank$', priority=5)
# 比赛信息查询命令
game = on_regex(r'^/game$', priority=5)
# 自动播报控制命令
open_broadcast = on_regex(r'^/open$', priority=5)
close_broadcast = on_regex(r'^/close$', priority=5)


@rank.handle()
async def handle_rank(bot: Bot, event: Event):
    """处理排行榜查询命令"""
    # 验证权限
    error_msg = await validate_command_prerequisites("rank", event)
    if error_msg:
        if error_msg == "PERMISSION_DENIED":
            return  # 静默处理权限拒绝
        await rank.finish(error_msg)

    try:
        async with httpx.AsyncClient() as client:
            # 获取比赛信息
            game_info_url = f"{GZCTF_BASE_URL}/api/game/{TARGET_GAME_ID}"
            game_info_response = await client.get(game_info_url, timeout=10.0)
            game_info_response.raise_for_status()
            game_info = game_info_response.json()
            game_title = game_info.get("title", "GZCTF")

            # 获取排行榜数据
            scoreboard_url = f"{GZCTF_BASE_URL}/api/game/{TARGET_GAME_ID}/scoreboard"
            scoreboard_response = await client.get(scoreboard_url, timeout=10.0)
            scoreboard_response.raise_for_status()
            data = scoreboard_response.json()

        # 解析数据 - 使用 items 字段获取完整排行榜
        items = data.get("items", [])
        if not items:
            await rank.finish("暂无排行榜数据。")

        # 提取所有队伍数据
        sorted_items = []
        for item in items:
            name = item.get("name", "未知队伍")
            team_rank = item.get("rank", 0)
            score = item.get("score", 0)
            sorted_items.append({"name": name, "score": score, "rank": team_rank})

        # 按照 rank 排序（如果 API 已经提供了排名）
        sorted_items.sort(key=lambda x: x["rank"])

        if not sorted_items:
            await rank.finish("暂无排行榜数据。")

        # 格式化排行榜消息
        rank_emojis = {1: "🥇", 2: "🥈", 3: "🥉"}
        total_teams = len(sorted_items)
        text_lines = [f"{game_title} 排行榜", "=" * 30]

        for item in sorted_items:
            team_rank = item['rank']
            name = item['name']
            score = item['score']

            # 前三名使用奖牌图标，其他使用序号
            if team_rank <= 3:
                emoji = rank_emojis[team_rank]
                text_lines.append(f"{emoji} {name} - {score}分")
            else:
                text_lines.append(f"{team_rank}. {name} - {score}分")

        text_lines.append("=" * 30)
        message = "\n".join(text_lines)
        await send_response(bot, event, message, "rank")


    except httpx.TimeoutException:
        await rank.finish("查询排行榜超时，请稍后重试。")
    except httpx.HTTPStatusError as e:
        await rank.finish(f"查询排行榜失败！")
    except Exception as e:
        log_database_error("rank", e)
        await rank.finish("查询排行榜失败！")


@game.handle()
async def handle_game(bot: Bot, event: Event):
    """处理比赛信息查询命令"""
    # 验证权限
    error_msg = await validate_command_prerequisites("game", event)
    if error_msg:
        if error_msg == "PERMISSION_DENIED":
            return  # 静默处理权限拒绝
        await game.finish(error_msg)

    try:
        # 构造 API URL
        api_url = f"{GZCTF_BASE_URL}/api/game/{TARGET_GAME_ID}"

        # 调用 API 获取比赛信息
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, timeout=10.0)
            response.raise_for_status()
            data = response.json()

        # 提取比赛信息
        title = data.get("title", "未知比赛")
        start_timestamp = data.get("start", 0)
        end_timestamp = data.get("end", 0)

        # 转换时间戳为可读格式（毫秒转秒）
        from datetime import datetime, timezone, timedelta

        # 使用东八区时区
        tz = timezone(timedelta(hours=8))

        if start_timestamp:
            start_time = datetime.fromtimestamp(start_timestamp / 1000, tz=tz)
            start_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
        else:
            start_str = "未设置"

        if end_timestamp:
            end_time = datetime.fromtimestamp(end_timestamp / 1000, tz=tz)
            end_str = end_time.strftime("%Y-%m-%d %H:%M:%S")
        else:
            end_str = "未设置"

        text_lines = [
            f"{title}",
            "=" * 30,
            f"开始时间: {start_str}",
            f"结束时间: {end_str}",
            f"比赛网址:{GZCTF_BASE_URL}/games/{TARGET_GAME_ID}",
            "=" * 30
        ]

        message = "\n".join(text_lines)
        await send_response(bot, event, message, "game")

    except httpx.TimeoutException:
        await game.finish("查询比赛信息超时，请稍后重试。")
    except httpx.HTTPStatusError as e:
        await game.finish(f"查询比赛信息失败！")
    except Exception as e:
        log_database_error("game", e)
        await game.finish("查询比赛信息失败！")


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

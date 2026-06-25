import json
import httpx
from typing import AsyncGenerator, List, Dict, Any
from config.cache_conf import redis_client
from config.settings import settings
from config.roles import get_role_prompt
from utils.logger import get_logger

logger = get_logger(__name__)


def _context_key(user_id: int) -> str:
    """获取用户上下文缓存的 Redis key"""
    return f"chat:context:{user_id}"


async def get_chat_context(user_id: int) -> List[Dict[str, str]]:
    """获取用户最近的对话上下文（JSON 数组）"""
    key = _context_key(user_id)
    data = await redis_client.get(key)
    if data:
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            logger.warning("用户 %d 的上下文解析失败，重置", user_id)
            return []
    return []


async def update_chat_context(user_id: int, messages: List[Dict[str, str]]):
    """更新用户上下文，自动截断至最大长度"""
    max_len = settings.CONTEXT_MAX_LENGTH
    if len(messages) > max_len:
        messages = messages[-max_len:]
    key = _context_key(user_id)
    await redis_client.setex(
        key,
        settings.CONTEXT_EXPIRE_SECONDS,
        json.dumps(messages, ensure_ascii=False)
    )
    logger.debug("用户 %d 上下文已更新，当前 %d 条", user_id, len(messages))


async def clear_chat_context(user_id: int):
    """清空用户上下文"""
    key = _context_key(user_id)
    await redis_client.delete(key)
    logger.info("用户 %d 上下文已清空", user_id)


async def stream_chat_completion(messages: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
    """
    调用阿里云 DashScope API，返回流式内容（逐词）
    messages 需包含 system 提示词和完整对话历史
    """
    headers = {
        "Authorization": f"Bearer {settings.ALI_API_KEY}",
        "Content-Type": "application/json",
        "X-DashScope-SSE": "enable"
    }
    payload = {
        "model": settings.ALI_MODEL,
        "messages": messages,
        "stream": True
    }

    logger.info("调用 AI API，消息数：%d", len(messages))
    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream("POST", settings.ALI_ENDPOINT, json=payload, headers=headers) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        json_data = json.loads(data)
                        delta = json_data.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue

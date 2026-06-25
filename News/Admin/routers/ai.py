import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.ai import ChatRequest, ChatHistoryResponse
from crud.ai import (
    get_chat_context, update_chat_context, clear_chat_context,
    stream_chat_completion
)
from config.roles import get_role_prompt
from utils import logger
from utils.auth import get_current_user
from models.users import User
from utils.response import success_response

router = APIRouter(prefix="/api/ai", tags=["AI"])


@router.post("/chat")
async def chat(
        request: ChatRequest,
        user: User = Depends(get_current_user),  # 需要登录，以便绑定上下文
):
    """
    流式对话接口，自动管理上下文（多轮记忆）
    """
    user_id = user.id
    logger.info("用户 %d 发起对话，角色：%s，内容：%s", user_id, request.role, request.content[:20])

    # 1. 获取历史上下文
    context = await get_chat_context(user_id)

    # 2. 构建消息列表（system + 历史 + 当前用户消息）
    system_prompt = get_role_prompt(request.role)
    messages = [
        {"role": "system", "content": system_prompt},
        *context,  # 历史消息（已包含 user/assistant 对）
        {"role": "user", "content": request.content}
    ]

    # 3. 流式生成，同时收集完整回复
    full_response = ""

    async def generate():
        nonlocal full_response
        try:
            async for chunk in stream_chat_completion(messages):
                full_response += chunk
                yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error("AI 流式生成失败：%s", str(e), exc_info=True)
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
        finally:
            # 4. 无论成功失败，只要 full_response 非空就保存上下文
            if full_response:
                new_context = context + [
                    {"role": "user", "content": request.content},
                    {"role": "assistant", "content": full_response}
                ]
                await update_chat_context(user_id, new_context)
                logger.info("用户 %d 对话已保存，当前上下文 %d 条", user_id, len(new_context))

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/history")
async def get_history(user: User = Depends(get_current_user)):
    """获取用户最近的对话记录（用于前端初始化）"""
    context = await get_chat_context(user.id)
    return success_response(data=context)


@router.delete("/context")
async def reset_context(user: User = Depends(get_current_user)):
    """清空用户对话上下文（重置会话）"""
    await clear_chat_context(user.id)
    return success_response(message="上下文已清空")

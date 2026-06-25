import traceback

from fastapi import HTTPException, Request
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.responses import JSONResponse
from fastapi import status

DEBUG_MODE = True


async def http_exception_handler(request: Request, exc: HTTPException):
    """
    处理 FastAPI 抛出的 HTTPException 异常（如 404、403 等）

    将 HTTP 异常转换为统一的 JSON 响应格式，便于前端统一处理。

    :param request: 当前请求对象（Request），可用于记录日志或获取 URL
    :param exc: 捕获到的 HTTPException 实例，包含状态码和错误详情
    :return: JSONResponse 对象，包含 code、message 和 data 字段，其中 code 与 HTTP 状态码一致
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,
            "message": exc.detail,
            "data": None
        }
    )


async def integrity_error_handler(request: Request, exc: IntegrityError):
    """
    处理 SQLAlchemy 的 IntegrityError（数据完整性错误，如唯一约束、外键约束违反）

    根据错误信息中的关键词，向用户返回友好的中文提示。若 DEBUG_MODE 开启，还会附加调试信息。

    :param request: 当前请求对象，用于在调试信息中记录 URL
    :param exc: IntegrityError 异常实例，包含底层数据库错误详情（exc.orig）
    :return: JSONResponse，状态码 400，包含 code=400、message（友好提示）和 data（调试信息或 None）
    """
    error_msg = str(exc.orig)
    if "user_name_UNIQUE" in error_msg or "Duplicate entry" in error_msg:
        detail = "用户名已存在"
    elif "FOREIGN KEY" in error_msg:  # 原代码写成了 "ForEIGN KEY"，修正大小写和拼写
        detail = "关联数据不存在"
    else:
        detail = "数据约束冲突，请检查后重新输入"

    error_data = None
    if DEBUG_MODE:
        error_data = {
            "error_type": "IntegrityError",
            "error_detail": error_msg,
            "path": str(request.url)
        }
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "code": 400,
            "message": detail,
            "data": error_data
        }
    )


async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
    """
    处理 SQLAlchemy 的通用数据库错误（不包含完整性约束冲突的其他数据库异常）

    这类错误通常表示数据库操作失败（如连接超时、SQL 语法错误等），
    在生产环境返回通用提示，调试模式下返回详细堆栈信息。

    :param request: 当前请求对象，用于记录 URL
    :param exc: SQLAlchemyError 异常实例
    :return: JSONResponse，状态码 500，包含 code=500、message（通用提示）和 data（调试信息或 None）
    """
    error_data = None
    if DEBUG_MODE:
        error_data = {
            "error_type": type(exc).__name__,
            "error_detail": str(exc),
            "traceback": traceback.format_exc(),
            "path": str(request.url)
        }

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": 500,
            "message": "数据库操作失败，请稍后重试",
            "data": error_data
        }
    )


async def unknown_error_handler(request: Request, exc: Exception):
    """
    处理所有未被上述处理器捕获的未知异常（兜底异常处理器）

    捕获任何未预期的 Python 异常，返回友好的内部错误信息，并在调试模式下输出详细堆栈。

    :param request: 当前请求对象，用于记录 URL
    :param exc: 捕获到的通用 Exception 实例
    :return: JSONResponse，状态码 500，包含 code=500、message（通用提示）和 data（调试信息或 None）
    """
    error_data = None
    if DEBUG_MODE:
        error_data = {
            "error_type": type(exc).__name__,
            "error_detail": str(exc),
            "traceback": traceback.format_exc(),
            "path": str(request.url)
        }

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER,
        content={
            "code": 500,
            "message": "服务器内部错误，请稍后重试",
            "data": error_data
        }
    )

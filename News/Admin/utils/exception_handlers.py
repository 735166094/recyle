from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from utils.exception import http_exception_handler, integrity_error_handler, sqlalchemy_error_handler, \
    unknown_error_handler


def register_exception_handlers(app):
    """
    注册全局异常处理器，将特定异常类型绑定到对应的处理函数。

    该函数在 FastAPI 应用启动时调用，用于统一处理应用中抛出的各类异常，
    确保所有接口返回格式统一的 JSON 响应，提升前端对接体验。

    :param app: FastAPI 应用实例（FastAPI 或 APIRouter 的父应用）
    :return: None
    :note: 当前实现中，将 IntegrityError 错误注册为了 InterruptedError，这很可能是一个笔误，
            正确应为 IntegrityError。若实际运行时捕获不到数据库完整性错误，请检查此处。
    """
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(InterruptedError, integrity_error_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_error_handler)
    app.add_exception_handler(Exception, unknown_error_handler)

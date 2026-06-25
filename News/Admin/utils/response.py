from fastapi.encoders import jsonable_encoder
from starlette.responses import JSONResponse


def success_response(message: str = "success", data=None):
    """
    构建并返回一个统一格式的成功响应 JSON 对象。

    该函数封装了 FastAPI/Starlette 的 JSONResponse，自动将数据编码为 JSON 兼容格式，
    并统一响应结构，方便前端按固定格式解析。

    Args:
        message (str): 响应的提示消息，默认为 "success"。
        data: 需要返回的业务数据，可以是任意 Python 对象（如 dict、list、ORM 模型等）。
              默认为 None。

    Returns:
        JSONResponse: Starlette 的 JSON 响应对象，包含以下结构：
            {
                "code": 200,        # 固定成功状态码
                "message": str,     # 传入的提示消息
                "data": object      # 经过 jsonable_encoder 编码后的业务数据
            }

    Note:
        - 使用 `jsonable_encoder` 可以正确处理 Pydantic 模型、日期时间、UUID 等非 JSON 原生类型。
        - 该函数适用于所有成功响应的场景（如 GET、POST、PUT 请求的成功返回）。
        - 若需要返回其他 HTTP 状态码（如 201 Created），可直接使用 `JSONResponse` 并设置 `status_code`。
    """
    content = {
        "code": 200,
        "message": message,
        "data": data
    }
    return JSONResponse(content=jsonable_encoder(content))

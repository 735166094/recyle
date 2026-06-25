import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """
    项目配置类
    """
    # 获取环境变量
    ALI_API_KEY = os.getenv("ALI_API_KEY", "")
    ALI_MODEL: str = os.getenv("ALI_MODEL", "qwen3-max-preview")
    ALI_API_SECRET = os.getenv("ALI_API_SECRET", "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions")

    # 上下文管理
    CONTEXT_MAX_LENGTH: int = 10  # 保留最近 N 条消息（用户+助手各算1条）
    CONTEXT_EXPIRE_SECONDS: int = 3600  # 1小时无活动自动过期


settings = Settings()

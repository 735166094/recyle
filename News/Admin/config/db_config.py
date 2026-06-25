from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession, create_async_engine

# 数据库URL
ASYNC_DATABASE_URL = "mysql+aiomysql://root:root@localhost3306/news?charset=utf8mb4"

# 创建异步引擎
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,  # 数据库URL
    echo=True,  # 是否打印SQL语句日志
    future=True,  # 是否使用异步模式
    pool_pre_ping=True,  # 是否检查数据库连接是否正常
    pool_recycle=3600,  # 数据库连接超时时间
    pool_size=10,  # 数据库连接池大小
    max_overflow=20,  # 数据库连接池溢出时允许的连接数
)

# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,  # 绑定异步引擎
    class_=AsyncSession,  # 指定会话类
    expire_on_commit=False,  # 是否在提交时自动过期
)


# 依赖项，用于获取数据库会话
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

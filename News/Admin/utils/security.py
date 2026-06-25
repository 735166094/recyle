from passlib.context import CryptContext

# 创建上下文密码
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_hash_password(password: str):
    """
    使用 bcrypt 算法对明文密码进行哈希加密

    :param password: 明文密码字符串（待加密的原始密码）
    :return: 加密后的密码哈希字符串（包含算法标识、盐值和密文，可直接存储到数据库）
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str):
    """
    验证明文密码是否与加密后的密码一致

    :param plain_password: 明文密码字符串
    :param hashed_password: 加密后的密码哈希字符串
    :return: 布尔值，True 表示一致，False 表示不一致
    """
    return pwd_context.verify(plain_password, hashed_password)

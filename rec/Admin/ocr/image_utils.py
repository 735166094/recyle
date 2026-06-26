import os
import logging
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile

logger = logging.getLogger(__name__)


class ImageProcessor:
    """图片处理工具类 """

    # 常量定义
    SUPPORTED_FORMATS = {'JPEG', 'PNG', 'JPG', 'WEBP'}
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    DEFAULT_MAX_SIZE = (1200, 1200)
    DEFAULT_QUALITY = 85
    THUMBNAIL_SIZE = (200, 200)

    @classmethod
    def compress_image(cls, image_file, max_size=None, quality=None, format='JPEG'):
        """
        压缩图片文件 

        Args:
            image_file: 上传的图片文件
            max_size: 最大尺寸 (宽, 高)，默认1200x1200
            quality: 图片质量 (1-100)，默认85
            format: 输出格式，默认JPEG

        Returns:
            处理后的图片文件对象
        """
        try:
            # 使用默认参数
            max_size = max_size or cls.DEFAULT_MAX_SIZE
            quality = quality or cls.DEFAULT_QUALITY

            # 验证输入
            if not image_file:
                logger.warning("压缩图片失败: 输入文件为空")
                return image_file

            # 打开图片
            with Image.open(image_file) as img:
                # 转换模式为RGB
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                elif img.mode != 'RGB':
                    img = img.convert('RGB')

                original_size = img.size

                # 计算新的尺寸，保持宽高比
                if original_size[0] > max_size[0] or original_size[1] > max_size[1]:
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)

                # 保存到内存
                output = BytesIO()
                img.save(output, format=format, quality=quality, optimize=True)
                output_size = output.getbuffer().nbytes
                output.seek(0)

                # 创建新的InMemoryUploadedFile
                compressed_file = InMemoryUploadedFile(
                    output,
                    'ImageField',
                    f"{os.path.splitext(image_file.name)[0]}_compressed.jpg",
                    f'image/{format.lower()}',
                    output_size,
                    None
                )

                # 记录压缩信息
                logger.info(
                    f"图片压缩完成: {original_size[0]}x{original_size[1]} -> "
                    f"{img.size[0]}x{img.size[1]}, 质量: {quality}%, "
                    f"大小: {output_size} bytes"
                )

                return compressed_file

        except Exception as e:
            logger.error(f"图片压缩失败: {str(e)}")
            # 如果压缩失败，返回原始文件
            return image_file

    @classmethod
    def validate_image_size(cls, image_file, max_file_size=None):
        """
        验证图片文件大小 

        Args:
            image_file: 图片文件
            max_file_size: 最大文件大小（字节），默认5MB

        Returns:
            tuple: (是否通过验证, 错误信息)
        """
        try:
            max_file_size = max_file_size or cls.MAX_FILE_SIZE

            # 获取文件大小
            if hasattr(image_file, 'size'):
                file_size = image_file.size
            else:
                current_pos = image_file.tell()
                image_file.seek(0, os.SEEK_END)
                file_size = image_file.tell()
                image_file.seek(current_pos)  # 恢复文件指针位置

            if file_size > max_file_size:
                error_msg = f"图片文件过大: {file_size} bytes > {max_file_size} bytes"
                logger.warning(error_msg)
                return False, error_msg

            return True, None

        except Exception as e:
            error_msg = f"验证图片大小失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    @classmethod
    def get_image_info(cls, image_file):
        """
        获取图片基本信息 

        Args:
            image_file: 图片文件

        Returns:
            dict: 图片信息
        """
        try:
            with Image.open(image_file) as img:
                return {
                    'format': img.format,
                    'mode': img.mode,
                    'size': img.size,
                    'width': img.size[0],
                    'height': img.size[1],
                    'is_animated': getattr(img, 'is_animated', False)
                }
        except Exception as e:
            logger.error(f"获取图片信息失败: {str(e)}")
            return {}

    @classmethod
    def create_thumbnail(cls, image_path, thumbnail_size=None, quality=None):
        """
        创建缩略图 

        Args:
            image_path: 原图路径
            thumbnail_size: 缩略图尺寸，默认200x200
            quality: 图片质量，默认85

        Returns:
            str: 缩略图路径
        """
        thumbnail_size = thumbnail_size or cls.THUMBNAIL_SIZE
        quality = quality or cls.DEFAULT_QUALITY

        try:
            with Image.open(image_path) as img:
                # 转换为RGB模式
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                else:
                    img = img.convert('RGB')

                img.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)

                # 生成缩略图路径
                dir_name = os.path.dirname(image_path)
                file_name = os.path.basename(image_path)
                name, ext = os.path.splitext(file_name)
                thumbnail_path = os.path.join(dir_name, f"{name}_thumbnail.jpg")

                img.save(thumbnail_path, 'JPEG', quality=quality, optimize=True)
                logger.info(f"缩略图创建成功: {thumbnail_path}")

                return thumbnail_path

        except Exception as e:
            logger.error(f"创建缩略图失败: {str(e)}")
            return None

    @classmethod
    def validate_image_format(cls, image_file):
        """
        验证图片格式 

        Args:
            image_file: 图片文件

        Returns:
            tuple: (是否支持该格式, 错误信息)
        """
        try:
            # 先检查文件扩展名
            file_name = getattr(image_file, 'name', '').lower()
            if file_name:
                file_ext = os.path.splitext(file_name)[1].lower().lstrip('.')
                if file_ext not in {'jpg', 'jpeg', 'png', 'webp'}:
                    return False, f"不支持的图片格式: {file_ext}"

            # 使用PIL验证实际格式
            with Image.open(image_file) as img:
                format = img.format
                if format and format.upper() in cls.SUPPORTED_FORMATS:
                    return True, None
                else:
                    return False, f"不支持的图片格式: {format}"

        except Exception as e:
            error_msg = f"验证图片格式失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    @classmethod
    def process_uploaded_image(cls, image_file, max_size=None, quality=None, create_thumbnail=False):
        """
        处理上传的图片 - 综合方法

        Args:
            image_file: 上传的图片文件
            max_size: 最大尺寸
            quality: 图片质量
            create_thumbnail: 是否创建缩略图

        Returns:
            dict: 处理结果
        """
        result = {
            'success': False,
            'compressed_file': None,
            'thumbnail_path': None,
            'errors': []
        }

        try:
            # 验证格式
            is_valid_format, format_error = cls.validate_image_format(image_file)
            if not is_valid_format:
                result['errors'].append(format_error)
                return result

            # 验证大小
            is_valid_size, size_error = cls.validate_image_size(image_file)
            if not is_valid_size:
                result['errors'].append(size_error)
                return result

            # 压缩图片
            compressed_file = cls.compress_image(image_file, max_size, quality)
            if compressed_file:
                result['compressed_file'] = compressed_file

                # 如果需要创建缩略图且图片已保存到磁盘
                if create_thumbnail and hasattr(compressed_file, 'temporary_file_path'):
                    thumbnail_path = cls.create_thumbnail(compressed_file.temporary_file_path())
                    if thumbnail_path:
                        result['thumbnail_path'] = thumbnail_path

            result['success'] = True

        except Exception as e:
            error_msg = f"处理上传图片失败: {str(e)}"
            logger.error(error_msg)
            result['errors'].append(error_msg)

        return result

    @classmethod
    def calculate_aspect_ratio(cls, width, height):
        """计算宽高比"""
        if height == 0:
            return 0
        return width / height

    @classmethod
    def calculate_new_size(cls, original_size, max_size):
        """计算保持宽高比的新尺寸"""
        original_width, original_height = original_size
        max_width, max_height = max_size

        ratio = min(max_width / original_width, max_height / original_height)
        new_width = int(original_width * ratio)
        new_height = int(original_height * ratio)

        return new_width, new_height

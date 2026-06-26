from django.apps import AppConfig

class OcrConfig(AppConfig):
    """OCR应用配置"""
    default_auto_field = "django.db.models.BigAutoField"
    name = "ocr"
    verbose_name = "OCR管理"

    def ready(self):
        """应用启动时执行"""
        # 注册信号
        import ocr.signals
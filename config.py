import os
from datetime import timedelta

class Config:
    """إعدادات التطبيق الأساسية"""
    
    # إعدادات قاعدة البيانات
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///sam_pro.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # إعدادات الأمان
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'sam-pro-secret-key-2025'
    WTF_CSRF_ENABLED = True
    
    # إعدادات الجلسة
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    
    # إعدادات التطبيق
    APP_NAME = "برنامج المحاسب الذكي"
    APP_VERSION = "1.0.0"
    COMPANY_NAME = "SAM PRO"
    
    # إعدادات التقارير
    REPORTS_PER_PAGE = 50
    MAX_EXPORT_RECORDS = 10000
    
    # إعدادات العملة
    DEFAULT_CURRENCY = "ل.س"
    CURRENCY_SYMBOL = "ل.س"
    
    # إعدادات التاريخ
    DATE_FORMAT = "%Y-%m-%d"
    DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
    
    # مجلدات التطبيق
    UPLOAD_FOLDER = 'uploads'
    BACKUP_FOLDER = 'backups'
    REPORTS_FOLDER = 'reports'
    
    # أحجام الملفات
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    @staticmethod
    def init_app(app):
        """تهيئة التطبيق"""
        # إنشاء المجلدات المطلوبة
        for folder in [Config.UPLOAD_FOLDER, Config.BACKUP_FOLDER, Config.REPORTS_FOLDER]:
            if not os.path.exists(folder):
                os.makedirs(folder)

class DevelopmentConfig(Config):
    """إعدادات بيئة التطوير"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """إعدادات بيئة الإنتاج"""
    DEBUG = False
    TESTING = False

class TestingConfig(Config):
    """إعدادات بيئة الاختبار"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

# إعدادات البيئة
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

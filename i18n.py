"""
国际化支持模块 - 为ST26模块提供多语言支持。

功能：
1. 支持中英文语言切换
2. 提供翻译字典和翻译函数
3. 错误消息国际化
4. 用户界面文本国际化

作者: SAYHELLO Team
版本: 1.0.0
"""

import logging
from typing import Dict, Optional, Any
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

TRANSLATIONS: Dict[str, Dict[str, str]] = {}

DEFAULT_LANGUAGE = 'zh'

LANGUAGE_NAMES = {
    'en': 'English',
    'zh': '中文'
}


def load_translations(config_path: Optional[str] = None) -> Dict[str, Dict[str, str]]:
    """
    加载翻译配置文件。
    
    Args:
        config_path: 翻译配置文件路径，如果为None则使用默认路径
        
    Returns:
        翻译字典
    """
    global TRANSLATIONS
    
    default_translations = {
        'en': {
            'app_title': 'SAYHELLO - ST26 Sequence Processor',
            'upload_title': 'Upload Excel File',
            'processing': 'Processing...',
            'success': 'Success',
            'error': 'Error',
            'download': 'Download',
            'view_results': 'View Results',
            'back': 'Back',
            'file_not_found': 'File not found',
            'invalid_format': 'Invalid file format',
            'missing_sheets': 'Missing required sheets',
            'use_template': 'Please use the template to upload data!',
            'sequence_too_long': 'Sequence length exceeds maximum allowed',
            'sequence_too_short': 'Sequence length is too short',
            'invalid_characters': 'Sequence contains invalid characters',
            'empty_sequence': 'Sequence cannot be empty',
            'data_security_warning': 'Data will be deleted when you close this page. The server does not save any data.',
            'confirm_close': 'Are you sure you want to close? Your data will be lost.',
            'loading': 'Loading...',
            'please_wait': 'Please wait while your file is being processed.',
            'conversion_complete': 'Conversion complete!',
            'download_xml': 'Download XML',
            'download_report': 'Download Report',
        },
        'zh': {
            'app_title': 'SAYHELLO - ST26序列处理器',
            'upload_title': '上传Excel文件',
            'processing': '处理中...',
            'success': '成功',
            'error': '错误',
            'download': '下载',
            'view_results': '查看结果',
            'back': '返回',
            'file_not_found': '文件未找到',
            'invalid_format': '无效的文件格式',
            'missing_sheets': '缺少必需的表单',
            'use_template': '请使用模版上传数据！',
            'sequence_too_long': '序列长度超出最大允许值',
            'sequence_too_short': '序列长度太短',
            'invalid_characters': '序列包含无效字符',
            'empty_sequence': '序列不能为空',
            'data_security_warning': '关闭此页面后，数据将被删除。服务器不会保存任何数据。',
            'confirm_close': '确定要关闭吗？您的数据将会丢失。',
            'loading': '加载中...',
            'please_wait': '请等待您的文件正在处理。',
            'conversion_complete': '转换完成！',
            'download_xml': '下载XML',
            'download_report': '下载报告',
        }
    }
    
    if config_path is None:
        config_path = Path(__file__).parent / "config" / "i18n.yaml"
    else:
        config_path = Path(config_path)
    
    if config_path.exists():
        try:
            import yaml
            with open(config_path, 'r', encoding='utf-8') as f:
                custom_translations = yaml.safe_load(f) or {}
            TRANSLATIONS = {**default_translations, **custom_translations}
            logger.info(f"Loaded translations from {config_path}")
        except Exception as e:
            logger.warning(f"Failed to load translations from {config_path}: {e}")
            TRANSLATIONS = default_translations
    else:
        TRANSLATIONS = default_translations
        logger.info("Using default translations")
    
    return TRANSLATIONS


def gettext(key: str, language: str = DEFAULT_LANGUAGE) -> str:
    """
    获取翻译文本。
    
    Args:
        key: 翻译键
        language: 语言代码 ('en' 或 'zh')
        
    Returns:
        翻译后的文本，如果键不存在则返回原文
    """
    if not TRANSLATIONS:
        load_translations()
    
    if language not in TRANSLATIONS:
        language = DEFAULT_LANGUAGE
    
    translations = TRANSLATIONS.get(language, TRANSLATIONS.get(DEFAULT_LANGUAGE, {}))
    
    result = translations.get(key)
    if result is None:
        default_translations = TRANSLATIONS.get(DEFAULT_LANGUAGE, {})
        result = default_translations.get(key)
        if result is None:
            logger.warning(f"Translation key '{key}' not found for language '{language}'")
            return key
    
    return result


def _(key: str, language: str = None) -> str:
    """
    简化的翻译函数别名。
    
    Args:
        key: 翻译键
        language: 语言代码，如果为None则使用默认语言
        
    Returns:
        翻译后的文本
    """
    if language is None:
        language = DEFAULT_LANGUAGE
    return gettext(key, language)


def set_language(language: str) -> bool:
    """
    设置当前语言。
    
    Args:
        language: 语言代码 ('en' 或 'zh')
        
    Returns:
        是否设置成功
    """
    if language in LANGUAGE_NAMES:
        global DEFAULT_LANGUAGE
        DEFAULT_LANGUAGE = language
        logger.info(f"Language set to {LANGUAGE_NAMES[language]}")
        return True
    else:
        logger.warning(f"Unsupported language: {language}")
        return False


def get_current_language() -> str:
    """
    获取当前语言。
    
    Returns:
        当前语言代码
    """
    return DEFAULT_LANGUAGE


def get_supported_languages() -> Dict[str, str]:
    """
    获取支持的语言列表。
    
    Returns:
        语言代码到语言名称的映射
    """
    return LANGUAGE_NAMES.copy()


def translate_error_message(error_key: str, language: str = None) -> str:
    """
    翻译错误消息。
    
    Args:
        error_key: 错误消息键
        language: 语言代码
        
    Returns:
        翻译后的错误消息
    """
    if language is None:
        language = DEFAULT_LANGUAGE
    
    error_translations = {
        'en': {
            'FILE_NOT_FOUND': 'File not found: {file}',
            'MISSING_SHEET': 'Missing required sheet: {sheet}',
            'INVALID_SEQUENCE': 'Invalid sequence: {sequence}',
            'SEQUENCE_TOO_LONG': 'Sequence length ({length}) exceeds maximum allowed ({max_length})',
            'SEQUENCE_TOO_SHORT': 'Sequence length ({length}) is below minimum ({min_length})',
            'INVALID_CHARACTER': 'Invalid character found: {char}',
            'EMPTY_SEQUENCE': 'Sequence cannot be empty',
            'CONVERSION_ERROR': 'Error during conversion: {error}',
            'TEMPLATE_REQUIRED': 'Please use the template to upload data! Excel file is missing required sheets.',
        },
        'zh': {
            'FILE_NOT_FOUND': '文件未找到: {file}',
            'MISSING_SHEET': '缺少必需的表单: {sheet}',
            'INVALID_SEQUENCE': '无效的序列: {sequence}',
            'SEQUENCE_TOO_LONG': '序列长度 ({length}) 超出最大允许值 ({max_length})',
            'SEQUENCE_TOO_SHORT': '序列长度 ({length}) 低于最小值 ({min_length})',
            'INVALID_CHARACTER': '发现无效字符: {char}',
            'EMPTY_SEQUENCE': '序列不能为空',
            'CONVERSION_ERROR': '转换过程中发生错误: {error}',
            'TEMPLATE_REQUIRED': '请使用模版上传数据！Excel文件缺少必需的表单。',
        }
    }
    
    lang_translations = error_translations.get(language, error_translations.get(DEFAULT_LANGUAGE, {}))
    
    translation = lang_translations.get(error_key)
    if translation is None:
        en_translation = error_translations.get('en', {}).get(error_key)
        translation = en_translation if en_translation else error_key
    
    return translation


def format_error_message(error_key: str, **kwargs) -> str:
    """
    格式化错误消息。
    
    Args:
        error_key: 错误消息键
        **kwargs: 格式化参数
        
    Returns:
        格式化后的错误消息
    """
    message = translate_error_message(error_key)
    try:
        return message.format(**kwargs)
    except KeyError as e:
        logger.warning(f"Missing format argument for error message: {e}")
        return message


class LanguageContext:
    """
    语言上下文管理器，用于临时切换语言。
    """
    
    def __init__(self, language: str):
        """
        初始化语言上下文。
        
        Args:
            language: 要切换的语言代码
        """
        self.language = language
        self.previous_language = DEFAULT_LANGUAGE
    
    def __enter__(self):
        """进入上下文，设置新语言。"""
        set_language(self.language)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文，恢复原语言。"""
        set_language(self.previous_language)
        return False


def get_language_from_accept_header(accept_header: str) -> str:
    """
    从HTTP Accept-Language头解析首选语言。
    
    Args:
        accept_header: HTTP Accept-Language头的值
        
    Returns:
        解析出的语言代码
    """
    if not accept_header:
        return DEFAULT_LANGUAGE
    
    languages = []
    for part in accept_header.split(','):
        if ';' in part:
            lang, _, quality = part.partition(';')
            lang = lang.strip().split('-')[0]
            try:
                quality = float(quality.split('=')[1])
            except (ValueError, IndexError):
                quality = 1.0
            languages.append((lang, quality))
        else:
            lang = part.strip().split('-')[0]
            languages.append((lang, 1.0))
    
    languages.sort(key=lambda x: -x[1])
    
    for lang, _ in languages:
        if lang in LANGUAGE_NAMES:
            return lang
    
    return DEFAULT_LANGUAGE


def init_app(app_language: str = DEFAULT_LANGUAGE) -> None:
    """
    初始化应用的国际化支持。
    
    Args:
        app_language: 应用默认语言
    """
    set_language(app_language)
    load_translations()
    logger.info(f"Internationalization initialized with language: {app_language}")


if __name__ == '__main__':
    load_translations()
    
    print(f"Supported languages: {list(LANGUAGE_NAMES.keys())}")
    print(f"Current language: {get_current_language()}")
    
    test_keys = ['app_title', 'upload_title', 'processing', 'use_template']
    
    print("\nTranslation examples:")
    for key in test_keys:
        en = gettext(key, 'en')
        zh = gettext(key, 'zh')
        print(f"  {key}: en='{en}', zh='{zh}'")

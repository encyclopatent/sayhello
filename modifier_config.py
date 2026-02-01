"""
修饰符名称配置文件
用于统一管理ST.26序列中修饰符的中英文名称
"""

# XML中使用的标准英文名称（写入XML文件）
MODIFIER_NAMES_EN = {
    'm': {
        'full': '2prime-O-methyl',
        'description': '2prime-O-methylation',
        'zh': '2\'-O-甲基化'
    },
    'f': {
        'full': '2prime-fluoro',
        'description': '2prime-fluoro',
        'zh': '2\'-氟代'
    },
    'e': {
        'full': '2prime-methoxyethyl',
        'description': '2prime-MOE',
        'zh': '2\'-甲氧基乙基'
    },
    's': {
        'full': 'phosphorothioate linkage',
        'description': 'phosphorothioate',
        'zh': '硫代磷酸酯键'
    },
    'pv': {
        'full': '5prime-vinylphosphonate',
        'description': '5prime-vinylphosphonate',
        'zh': '5\'-乙烯基膦酸酯'
    }
}

# 序列摘要中使用的默认中文名称（用于网页显示）
MODIFIER_NAMES_ZH_DEFAULT = {
    'm': '甲基',
    'f': '氟',
    'e': '甲氧基乙基',
    's': '硫代',
    'pv': '乙烯基膦酸酯'
}

# 碱基名称映射（用于拼接完整的修饰名称）
BASE_NAMES_EN = {
    'A': 'adenosine',
    'C': 'cytidine',
    'G': 'guanosine',
    'U': 'uridine',
    'T': 'thymidine'
}

BASE_NAMES_ZH = {
    'A': '腺苷',
    'C': '胞苷',
    'G': '鸟苷',
    'U': '尿苷',
    'T': '胸苷'
}

def get_modifier_name_en(modifier: str, base: str = None, custom_names: dict = None) -> str:
    """
    获取修饰符的英文名称（用于XML）

    Args:
        modifier: 修饰符类型 (m, f, e, s, pv)
        base: 碱基 (A, C, G, U, T)，仅对m和f有效
        custom_names: 用户自定义英文名称字典，键为 'mEn', 'fEn', 'eEn', 'sEn', 'pvEn'

    Returns:
        英文名称
    """
    # 如果用户提供了自定义英文名称，使用自定义名称
    if custom_names and isinstance(custom_names, dict):
        custom_key = f"{modifier}En"
        if custom_key in custom_names and custom_names[custom_key]:
            custom_name = custom_names[custom_key]
            # 对于m和f修饰符，需要替换碱基占位符
            if modifier in ['m', 'f'] and base:
                base_name = BASE_NAMES_EN.get(base.upper(), 'base')
                # 将 {base} 替换为实际碱基名称
                return custom_name.replace('{base}', base_name)
            return custom_name

    # 否则使用默认英文名称
    if modifier not in MODIFIER_NAMES_EN:
        return modifier

    mod_info = MODIFIER_NAMES_EN[modifier]

    # 对于m和f修饰符，需要拼接碱基名称
    if modifier in ['m', 'f'] and base:
        base_name = BASE_NAMES_EN.get(base.upper(), 'base')
        return f"{mod_info['full']} {base_name}"

    return mod_info['full']


def _format_prime_symbol(text: str, prime_format: str) -> str:
    """
    根据指定的格式转换文本中的 prime 符号

    Args:
        text: 包含 'prime' 关键字的文本
        prime_format: 格式类型
            - 'prime': 保持 'prime' (默认，如 2prime-O-methyl)
            - 'quote': 使用单引号 (如 2'-O-methyl)
            - 'sup': 使用上标字符 (如 2⁽ᵐᵉ⁾-O-methyl)

    Returns:
        转换后的文本
    """
    if prime_format == 'prime':
        # 保持默认的 'prime' 格式
        return text
    elif prime_format == 'quote':
        # 将 'prime' 替换为单引号
        # 2prime -> 2', 5prime -> 5'
        return text.replace('prime', "'")
    elif prime_format == 'sup':
        # 使用上标字符
        # 2prime -> 2⁽ᵐᵉ⁾ (不太常用，但提供选项)
        return text.replace('2prime', '2⁽ᵐᵉ⁾').replace('5prime', '5⁽ᵛᵉ⁾')
    else:
        # 未知格式，返回原文本
        return text

def get_modifier_name_zh(modifier: str, custom_names: dict = None) -> str:
    """
    获取修饰符的中文名称（用于摘要显示）

    Args:
        modifier: 修饰符类型 (m, f, e, s, pv)
        custom_names: 用户自定义名称字典 {'m': '...', 'f': '...', 's': '...'}

    Returns:
        中文名称
    """
    # 如果用户提供了自定义名称，使用自定义名称
    if custom_names and modifier in custom_names and custom_names[modifier]:
        return custom_names[modifier]

    # 否则使用默认中文名称
    return MODIFIER_NAMES_ZH_DEFAULT.get(modifier, modifier)

def get_all_modifier_info() -> dict:
    """
    获取所有修饰符的完整信息

    Returns:
        包含所有修饰符信息的字典
    """
    return {
        mod: {
            'en': MODIFIER_NAMES_EN[mod],
            'zh_default': MODIFIER_NAMES_ZH_DEFAULT[mod],
            'bases': BASE_NAMES_EN if mod in ['m', 'f'] else None
        }
        for mod in MODIFIER_NAMES_EN
    }

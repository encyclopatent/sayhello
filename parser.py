# parser.py
"""
序列解析模块 - 用于解析核酸和蛋白质序列，支持ST26标准格式。

主要功能：
1. 解析DNA、RNA和蛋白质序列
2. 处理各种修饰类型（甲基化、氟化、硫代等）
3. 支持新格式和旧格式的修饰标注转换
4. 验证序列的合法性

作者: SAYHELLO Team
版本: 2.0.0
"""

import logging
from modifier_config import MODIFIER_NAMES_ZH_DEFAULT, get_modifier_name_zh
import re
from typing import Dict, List, Optional, Set, Tuple, Any
from pathlib import Path

import pandas as pd

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============ 配置管理类 ============

class ST26Config:
    """
    ST26 配置管理类（单例模式）
    用于管理所有配置和常量，避免全局变量污染
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._config: Dict[str, Any] = {}
            self._base_names: Dict[str, Dict[str, str]] = {}
            self._valid_aa: Set[str] = set()
            self._predefined_mods: Set[str] = set()
            self._dna_to_aa: Dict[str, str] = {}
            self._modifier_chars: Set[str] = set()
            self._degenerate_bases: Set[str] = set()
            self._load_default_values()
            self._initialized = True

    def _load_default_values(self):
        """加载默认配置值"""
        # 默认碱基名称
        self._base_names = {
            'A': {'en': 'adenosine', 'zh': '腺苷'},
            'U': {'en': 'uridine',   'zh': '尿苷'},
            # ... 其他值
        }

        # 默认修饰符字符
        self._modifier_chars = {'m', 'f', 's', 'p', 'e', 'b', 'd', 'r'}

        # 默认简并碱基
        self._degenerate_bases = {'R', 'Y', 'M', 'K', 'S', 'W', 'H', 'B', 'V', 'D', 'N'}

    @property
    def base_names(self) -> Dict[str, Dict[str, str]]:
        return self._base_names

    @property
    def valid_aa(self) -> Set[str]:
        return self._valid_aa

    @property
    def predefined_mods(self) -> Set[str]:
        return self._predefined_mods

    @property
    def modifier_chars(self) -> Set[str]:
        return self._modifier_chars

    @property
    def degenerate_bases(self) -> Set[str]:
        return self._degenerate_bases

    def load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """
        加载配置文件

        Args:
            config_path: 配置文件路径

        Returns:
            配置字典
        """
        if not YAML_AVAILABLE:
            logger.warning("PyYAML not installed, using default configuration")
            return self._config

        if config_path is None:
            config_path = Path(__file__).parent / "config" / "st26.yaml"
        else:
            config_path = Path(config_path)

        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    self._config = yaml.safe_load(f) or {}
                logger.info(f"Loaded configuration from {config_path}")
                self._update_constants_from_config()
            except Exception as e:
                logger.error(f"Failed to load configuration: {e}")
        else:
            logger.warning(f"Configuration file not found: {config_path}")

        return self._config

    def _update_constants_from_config(self):
        """从配置更新常量"""
        if 'base_names' in self._config:
            self._base_names.update(self._config['base_names'])

        if 'modifications' in self._config:
            mods_config = self._config['modifications']
            if 'valid_amino_acids' in mods_config:
                self._valid_aa = set(mods_config['valid_amino_acids'])
            if 'modifiers' in mods_config:
                self._modifier_chars = set(mods_config['modifiers'])
            if 'degenerate_bases' in mods_config:
                self._degenerate_bases = set(mods_config['degenerate_bases'])

        if 'predefined_modifications' in self._config:
            self._predefined_mods = set(self._config['predefined_modifications'])

    def get_value(self, key: str, default: Any = None) -> Any:
        """
        获取配置值

        Args:
            key: 配置键，支持点号分隔的嵌套键
            default: 默认值

        Returns:
            配置值或默认值
        """
        if not self._config:
            return default

        keys = key.split('.')
        value = self._config

        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default


# 创建全局配置实例
_config_instance = ST26Config()


# ============ 兼容性函数（保持向后兼容）============

def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """加载配置文件（兼容性函数）"""
    return _config_instance.load_config(config_path)


def _get_config_value(key: str, default: Any = None) -> Any:
    """从配置中获取值（兼容性函数）"""
    return _config_instance.get_value(key, default)


# 保留全局 CONFIG 以保持向后兼容
CONFIG = {}

def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    加载配置文件。
    
    Args:
        config_path: 配置文件路径，如果为None则使用默认路径
        
    Returns:
        配置字典
    """
    global CONFIG
    
    if not YAML_AVAILABLE:
        logger.warning("PyYAML not installed, using default configuration")
        return CONFIG
    
    if config_path is None:
        config_path = Path(__file__).parent / "config" / "st26.yaml"
    else:
        config_path = Path(config_path)
    
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                CONFIG = yaml.safe_load(f) or {}
            logger.info(f"Loaded configuration from {config_path}")
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            CONFIG = {}
    else:
        logger.warning(f"Configuration file not found: {config_path}")
    
    return CONFIG

def _get_config_value(key: str, default: Any = None) -> Any:
    """
    从配置中获取值，如果配置未加载则返回默认值。
    
    Args:
        key: 配置键，支持点号分隔的嵌套键
        default: 默认值
        
    Returns:
        配置值或默认值
    """
    if not CONFIG:
        return default
    
    keys = key.split('.')
    value = CONFIG
    
    try:
        for k in keys:
            value = value[k]
        return value
    except (KeyError, TypeError):
        return default

def _init_constants_from_config() -> None:
    """从配置初始化常量。"""
    global BASE_NAMES, VALID_AA, PREDEFINED_MODS, DNA_TO_AA
    
    config = load_config()
    
    if config and 'base_names' in config:
        BASE_NAMES = config['base_names']
    
    if config and 'modifications' in config:
        mods_config = config['modifications']
        if 'valid_amino_acids' in mods_config:
            VALID_AA = set(mods_config['valid_amino_acids'])
        if 'modifiers' in mods_config:
            MODIFIER_CHARS = set(mods_config['modifiers'])
        if 'degenerate_bases' in mods_config:
            DEGENERATE_BASES = set(mods_config['degenerate_bases'])
    
    if config and 'predefined_modifications' in config:
        PREDEFINED_MODS = set(config['predefined_modifications'])
    
    if config and 'dna_codon_table' in config:
        DNA_TO_AA = config['dna_codon_table']

BASE_NAMES = {
    'A': {'en': 'adenosine', 'zh': '腺苷'},
    'U': {'en': 'uridine',   'zh': '尿苷'},
    'C': {'en': 'cytidine',  'zh': '胞苷'},
    'G': {'en': 'guanosine', 'zh': '鸟苷'},
    'T': {'en': 'thymidine', 'zh': '胸苷'}
}

VALID_AA = {
    'A', 'R', 'N', 'D', 'C', 'Q', 'E', 'G', 'H', 'I', 
    'L', 'K', 'M', 'F', 'P', 'O', 'S', 'U', 'T', 'W', 
    'Y', 'V', 'B', 'Z', 'J', 'X', 'x'
}

PREDEFINED_MODS = {
    'ac4c', 'chm5u', 'cm', 'cmnm5s2u', 'cmnm5u', 'dhu', 'fm', 'galq', 'gm', 'i', 'i6a', 'm1a', 'm1f', 'm1g', 'm1i',
    'm22g', 'm2a', 'm2g', 'm3c', 'm4c', 'm5c', 'm6a', 'm7g', 'mam5u', 'mam5s2u', 'manq', 'mcm5s2u', 'mcm5u', 'mo5u',
    'ms2i6a', 'ms2t6a', 'mt6a', 'mv', 'o5u', 'osyw', 'p', 'q', 's2c', 's2t', 's2u', 's4u', 'm5u', 't6a', 'tm', 'um', 'yw', 'x'
}

DEGENERATE_BASES = {'M', 'R', 'W', 'S', 'Y', 'K', 'V', 'H', 'D', 'B'}

MODIFIER_CHARS = {'m', 'f', 'e', 's', 'pv'}

DNA_TO_AA = {
    'TTT': 'F', 'TTC': 'F', 'TTA': 'L', 'TTG': 'L',
    'CTT': 'L', 'CTC': 'L', 'CTA': 'L', 'CTG': 'L',
    'ATT': 'I', 'ATC': 'I', 'ATA': 'I', 'ATG': 'M',
    'GTT': 'V', 'GTC': 'V', 'GTA': 'V', 'GTG': 'V',
    'TCT': 'S', 'TCC': 'S', 'TCA': 'S', 'TCG': 'S',
    'CCT': 'P', 'CCC': 'P', 'CCA': 'P', 'CCG': 'P',
    'ACT': 'T', 'ACC': 'T', 'ACA': 'T', 'ACG': 'T',
    'GCT': 'A', 'GCC': 'A', 'GCA': 'A', 'GCG': 'A',
    'TAT': 'Y', 'TAC': 'Y', 'TAA': '*', 'TAG': '*',
    'CAT': 'H', 'CAC': 'H', 'CAA': 'Q', 'CAG': 'Q',
    'AAT': 'N', 'AAC': 'N', 'AAA': 'K', 'AAG': 'K',
    'GAT': 'D', 'GAC': 'D', 'GAA': 'E', 'GAG': 'E',
    'TGT': 'C', 'TGC': 'C', 'TGA': '*', 'TGG': 'W',
    'CGT': 'R', 'CGC': 'R', 'CGA': 'R', 'CGG': 'R',
    'AGT': 'S', 'AGC': 'S', 'AGA': 'R', 'AGG': 'R',
    'GGT': 'G', 'GGC': 'G', 'GGA': 'G', 'GGG': 'G'
}

PV_PREFIX_PATTERNS = [
    (r'^[Pp][Vv]-', 3),
    (r'^[Vv][Pp]-', 3),
    (r'^[Pp][Vv]', 2),
    (r'^[Vv][Pp]', 2),
]


def validate_sequence_length(sequence: str, max_length: Optional[int] = None, min_length: int = 1) -> Tuple[bool, str]:
    """
    验证序列长度是否在有效范围内。
    
    Args:
        sequence: 待验证的序列
        max_length: 最大长度，默认从配置读取
        min_length: 最小长度
        
    Returns:
        (是否有效, 错误信息)
    """
    if max_length is None:
        max_length = _get_config_value('sequence.max_length', 10000)
    
    seq_len = len(sequence)
    
    if seq_len < min_length:
        return False, f"序列长度不能小于{min_length}"
    
    if seq_len > max_length:
        return False, f"序列长度超出限制: {seq_len} > {max_length}"
    
    return True, ""


def validate_sequence_chars(sequence: str, moltype: str) -> Tuple[bool, str]:
    """
    验证序列是否包含非法字符。
    
    Args:
        sequence: 待验证的序列
        moltype: 分子类型 (DNA, RNA, AA)
        
    Returns:
        (是否有效, 错误信息)
    """
    moltype_upper = moltype.upper()
    
    if moltype_upper == "AA":
        invalid_chars = set(re.findall(r'[^A-Z]', sequence.upper()))
        if invalid_chars:
            return False, f"蛋白质序列包含非法字符: {invalid_chars}"
    else:
        invalid_chars = set(re.findall(r'[^a-zA-Z]', sequence))
        if invalid_chars:
            return False, f"核酸序列包含非法字符: {invalid_chars}"
    
    return True, ""


def sanitize_filename(filename: str) -> str:
    """
    净化文件名，移除危险字符。
    
    Args:
        filename: 原始文件名
        
    Returns:
        净化后的安全文件名
    """
    return re.sub(r'[^\w\-.]', '_', filename)


def split_chinese_english(text: str) -> Tuple[str, Optional[str]]:
    """
    分离中英文文本。
    
    Args:
        text: 混合文本
        
    Returns:
        (英文部分, 中文部分)
    """
    chinese_chars = []
    english_chars = []
    
    for char in text:
        if '\u4e00' <= char <= '\u9fa5':
            chinese_chars.append(char)
        else:
            english_chars.append(char)
    
    english_part = ''.join(english_chars).strip()
    chinese_part = ''.join(chinese_chars) if chinese_chars else None
    
    return english_part, chinese_part


def convert_new_format_to_old(seq: str) -> Tuple[str, bool]:
    """
    将新格式的修饰标注转换为旧格式。
    
    新格式示例: (VP)(mG)*(mG)*(mU)(mU)(fG)(mG)(fA)(mU)(fU)(fU)(fU)(mU)(fC)(mU)(mU)(mG)(mC)(mU)(mA)(mU)(mG)(L96)
    旧格式示例: VPmG*s*mG*s*mUmUfGmGfAmUfUfUfUmUfCmUmUmGmCmUmAmUmGL96
    
    其中 * 代表 s 修饰，括号里m和f在被修饰的碱基左侧。
    旧格式要求：碱基 + 修饰符 + 连接修饰
    
    Args:
        seq: 输入序列
        
    Returns:
        (转换后的序列, 是否移除了配体)
    """
    logger.debug(f"Converting sequence format: {seq[:50]}...")
    
    if not seq.startswith('('):
        return seq, False
    
    pattern = r'\(([^)]+)\)(\*)?'
    matches = re.findall(pattern, seq)
    
    if not matches:
        return seq, False
    
    matched_seq = ''
    for content, star_mod in matches:
        matched_seq += f'({content})'
        if star_mod:
            matched_seq += star_mod
    
    if matched_seq != seq:
        logger.warning(f"Sequence format mismatch, returning original: {seq[:50]}...")
        return seq, False
    
    converted: List[str] = []
    ligand_removed = False
    
    for i, (content, star_mod) in enumerate(matches):
        content_upper = content.upper()
        if content_upper in ('L96', '-L96'):
            ligand_removed = True
            logger.debug(f"Removed ligand L96 from position {i}")
            continue
        
        if content_upper in ('VP', 'PV', 'PV-', 'VP-'):
            if i == 0:
                clean_content = content.replace('-', '')
                converted.append(clean_content)
            continue
        
        modifiers: List[str] = []
        base = ''
        
        for char in content:
            if char in 'mf':
                modifiers.append(char)
            elif char.lower() in 'agcut':
                base = char
                remaining = content[content.index(char)+1:]
                for remaining_char in remaining:
                    if remaining_char in 'mf':
                        modifiers.append(remaining_char)
                break
        
        if not base:
            converted.append(f'({content})')
            if star_mod:
                converted.append(star_mod)
            continue
        
        converted.append(base)
        converted.extend(modifiers)
        
        if star_mod:
            converted.append('s')
    
    result = ''.join(converted)
    logger.debug(f"Converted sequence: {result[:50]}...")
    return result, ligand_removed


def parse_sequence(
    seq: str,
    moltype: Optional[str],
    line_number: Optional[int] = None
) -> Tuple[str, List[Tuple[int, str, Optional[str]]], List[int], Optional[str], bool, bool]:
    """
    解析序列，提取修饰和特殊位置。

    Args:
        seq: 输入序列字符串
        moltype: 分子类型 (DNA, RNA, AA)
        line_number: 行号，用于错误提示

    Returns:
        Tuple包含:
        - final_naked_sequence: 清洁后的序列
        - modifications: 修饰列表 [(位置, 修饰类型, 碱基), ...]
        - special_positions: 特殊位置列表
        - raw_moltype: 原始分子类型
        - has_degenerate_bases: 是否包含简并碱基
        - ligand_removed: 是否移除了配体

    Raises:
        ValueError: 序列包含非法字符
    """
    if not isinstance(seq, str):
        error_msg = "输入序列必须是字符串类型"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    seq = seq.strip().replace(" ", "")
    
    valid, error_msg = validate_sequence_length(seq)
    if not valid:
        logger.error(f"Sequence length validation failed: {error_msg}")
        raise ValueError(error_msg)
    
    logger.info(f"Parsing sequence (line {line_number}): type={moltype}, length={len(seq)}")
    
    seq, new_format_ligand_removed = convert_new_format_to_old(seq)
    naked_sequence: List[str] = []
    modifications: List[Any] = []
    special_positions: List[int] = []
    i = 0
    raw_moltype = moltype
    moltype = moltype.upper() if pd.notnull(moltype) else "RNA"
    has_degenerate_bases = False
    ligand_removed = new_format_ligand_removed
    
    if moltype in ("RNA", "DNA"):
        seq_len = len(seq)
        if seq_len >= 3 and seq[-3:].upper() == "L96":
            seq = seq[:-3]
            ligand_removed = True
            logger.debug("Removed L96 ligand from end")
        elif seq_len >= 4 and seq[-4:].upper() == "-L96":
            seq = seq[:-4]
            ligand_removed = True
            logger.debug("Removed -L96 ligand from end")
    
    if moltype in ("RNA", "DNA"):
        seq_len = len(seq)
        for pattern, length in PV_PREFIX_PATTERNS:
            if seq_len >= length:
                match = re.match(pattern, seq)
                if match:
                    mod_end_pos = len(match.group(0))
                    if mod_end_pos < seq_len:
                        base_after_mod = seq[mod_end_pos].lower()
                        modifications.append((1, 'pv', base_after_mod))
                        seq = seq[mod_end_pos:]
                        logger.debug(f"Detected pv modification at position 1")
                        break
    
    seq_len = len(seq)
    while i < seq_len:
        current_char = seq[i]
        
        if moltype == "AA":
            current_char_upper = current_char.upper()
            if current_char_upper not in VALID_AA:
                error_msg = f"字符 '{current_char}' 并非系统允许的氨基酸表示"
                if line_number:
                    error_msg = f"第{line_number}行第{len(naked_sequence)+1}号氨基酸：{error_msg}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            naked_sequence.append(current_char_upper)
            if current_char_upper == 'X':
                special_positions.append(len(naked_sequence))
            i += 1
        else:
            if current_char in MODIFIER_CHARS:
                modifiers: List[str] = []
                while i < seq_len and seq[i] in MODIFIER_CHARS:
                    modifiers.append(seq[i].lower())
                    i += 1
                
                if i >= seq_len:
                    continue
                    
                base_char = seq[i]
                base_char_lower = base_char.lower()
                
                if base_char in DEGENERATE_BASES:
                    has_degenerate_bases = True
                    naked_sequence.append(base_char)
                    current_base_pos = len(naked_sequence)
                    i += 1
                elif base_char_lower in 'agcut':
                    naked_sequence.append(base_char)
                    current_base_pos = len(naked_sequence)
                    i += 1
                else:
                    i += 1
                    continue
                    
                for mod in modifiers:
                    if mod in ('m', 'f', 'e'):
                        modifications.append((current_base_pos, mod, base_char_lower))
                    elif mod == 's' and i < seq_len and seq[i].lower() in 'agcut':
                        modifications.append((f"{current_base_pos}^{current_base_pos + 1}", 's', base_char_lower))
            
            elif current_char in DEGENERATE_BASES:
                has_degenerate_bases = True
                naked_sequence.append(current_char)
                current_base_pos = len(naked_sequence)
                base_char_lower = current_char.lower()
                i += 1
                
                if i < seq_len and seq[i] in MODIFIER_CHARS:
                    modifiers = []
                    while i < seq_len and seq[i] in MODIFIER_CHARS:
                        modifiers.append(seq[i].lower())
                        i += 1
                    
                    for mod in modifiers:
                        if mod in ('m', 'f', 'e'):
                            modifications.append((current_base_pos, mod, base_char_lower))
                        elif mod == 's' and i < seq_len and seq[i].lower() in 'agcut':
                            modifications.append((f"{current_base_pos}^{current_base_pos + 1}", 's', base_char_lower))
            
            elif current_char.lower() in 'agcut':
                naked_sequence.append(current_char)
                current_base_pos = len(naked_sequence)
                base_char_lower = current_char.lower()
                i += 1
                
                if i < seq_len and seq[i] in MODIFIER_CHARS:
                    modifiers = []
                    while i < seq_len and seq[i] in MODIFIER_CHARS:
                        modifiers.append(seq[i].lower())
                        i += 1
                    
                    for mod in modifiers:
                        if mod in ('m', 'f', 'e'):
                            modifications.append((current_base_pos, mod, base_char_lower))
                        elif mod == 's' and i < seq_len and seq[i].lower() in 'agcut':
                            modifications.append((f"{current_base_pos}^{current_base_pos + 1}", 's', base_char_lower))
            
            elif current_char.upper() == 'N':
                naked_sequence.append(current_char)
                if moltype in ("DNA", "RNA"):
                    special_positions.append(len(naked_sequence))
                i += 1
            else:
                if seq[i].islower() and seq[i] not in MODIFIER_CHARS:
                    error_msg = f"小写字母为修饰方式，输入了不能处理的修饰方式 '{seq[i]}'"
                else:
                    error_msg = f"字符 '{seq[i]}' 并非系统允许的碱基表示"
                
                if line_number:
                    error_msg = f"第{line_number}行序列位置 {i+1} 处：{error_msg}"
                
                logger.error(error_msg)
                raise ValueError(error_msg)
    
    base_sequence = ''.join(naked_sequence)
    
    if moltype == "AA":
        final_naked_sequence = base_sequence
    else:
        final_naked_sequence = base_sequence.translate(str.maketrans('uU', 'tT'))
    
    logger.info(f"Parsed sequence successfully: length={len(final_naked_sequence)}, "
                f"modifications={len(modifications)}, degenerate_bases={has_degenerate_bases}")
    
    return final_naked_sequence, modifications, special_positions, raw_moltype, has_degenerate_bases, ligand_removed


def read_basic_data_from_excel(file_path: str) -> Dict[str, str]:
    """
    从Excel文件读取基础数据。
    
    Args:
        file_path: Excel文件路径
        
    Returns:
        基础数据字典
        
    Raises:
        ValueError: 当缺少必需的sheet时
    """
    logger.info(f"Reading basic data from: {file_path}")
    
    try:
        df = pd.read_excel(file_path, sheet_name='basicdata', engine='openpyxl')
    except ValueError as e:
        logger.error("basicdata sheet not found")
        raise ValueError("请使用模版上传数据！Excel文件中缺少必需的sheet（basicdata）。")
    
    df.dropna(how='all', inplace=True)
    basic_data: Dict[str, str] = {}
    
    field_col = next((
        col for col in df.columns 
        if any(keyword in str(col).lower() for keyword in ['field', '字段', '项'])
    ), None)
    value_col = next((
        col for col in df.columns 
        if any(keyword in str(col).lower() for keyword in ['value', '值', '内容'])
    ), None)
    
    if field_col is None:
        field_col = df.columns[0]
    if value_col is None and len(df.columns) > 1:
        value_col = df.columns[1]
    
    for index, row in df.iterrows():
        field = row[field_col]
        value = row[value_col]
        
        if pd.notna(field) and pd.notna(value):
            field_str = str(field).strip()
            value_str = str(value).strip()
            basic_data[field_str] = value_str
    
    logger.info(f"Read {len(basic_data)} basic data entries")
    return basic_data


# ============ 正则表达式常量（预编译以提高性能）============

# 中文区段匹配
_SEGMENT_PATTERN = re.compile(r'第[一二三四五六七八九十]+区段')
_CHINESE_NUM_PATTERN = re.compile(r'第([一二三四五六七八九十]+)区段')

# 环状结构匹配
_RING_PATTERN = re.compile(r'region\s*[:：]?\s*(\d+)\.\.(\d+).*note\s*[:：]?\s*(.+)', re.I)

# 杂合段匹配
_HYBRID_SEGMENT_PATTERN1 = re.compile(r'\s*(\d+)\s*\.\.\s*(\d+)\s*(RNA|DNA)\s*', re.IGNORECASE)
_HYBRID_SEGMENT_PATTERN2 = re.compile(r'\s*(\d+)\s*-\s*(\d+)\s*(RNA|DNA)\s*', re.IGNORECASE)
_HYBRID_SEGMENT_PATTERN3 = re.compile(r'\s*(\d+)\s+(RNA|DNA)\s*', re.IGNORECASE)


def read_sequences_from_excel(file_path: str) -> List[Dict[str, Any]]:
    """
    从Excel文件读取序列数据。
    
    Args:
        file_path: Excel文件路径
        
    Returns:
        序列数据列表
        
    Raises:
        ValueError: 当缺少必需的sheet时
    """
    logger.info(f"Reading sequences from: {file_path}")
    
    try:
        df = pd.read_excel(file_path, sheet_name='seqdata', engine='openpyxl')
    except ValueError as e:
        logger.error("seqdata sheet not found")
        raise ValueError("请使用模版上传数据！Excel文件中缺少必需的sheet（seqdata）。")
    
    df.dropna(how='all', inplace=True)

    col_names = [str(col).lower() for col in df.columns]

    # 使用预编译的正则表达式常量
    segment_pattern = _SEGMENT_PATTERN
    chinese_num_pattern = _CHINESE_NUM_PATTERN
    ring_pattern = _RING_PATTERN
    hybrid_segment_pattern1 = _HYBRID_SEGMENT_PATTERN1
    hybrid_segment_pattern2 = _HYBRID_SEGMENT_PATTERN2
    hybrid_segment_pattern3 = _HYBRID_SEGMENT_PATTERN3

    seq_col = None
    for i, col in enumerate(col_names):
        if any(keyword in col for keyword in ['序列', 'sequence', 'seq']):
            seq_col = df.columns[i]
            break
    if seq_col is None:
        seq_col = df.columns[0]
    
    moltype_col = None
    for i, col in enumerate(col_names):
        if any(keyword in col for keyword in ['分子类型', 'moltype', '类型']):
            moltype_col = df.columns[i]
            break
    if moltype_col is None and len(df.columns) > 1:
        moltype_col = df.columns[1]
    
    organism_col = None
    for i, col in enumerate(col_names):
        if any(keyword in col for keyword in ['来源', 'organism', 'source']):
            organism_col = df.columns[i]
            break
    if organism_col is None and len(df.columns) > 2:
        organism_col = df.columns[2]
    
    qual_moltype_col = None
    for i, col in enumerate(col_names):
        if any(keyword in col for keyword in ['修饰类型', 'qualifier', 'qual_moltype']):
            qual_moltype_col = df.columns[i]
            break
    if qual_moltype_col is None and len(df.columns) > 3:
        qual_moltype_col = df.columns[3]
    
    ring_col = None
    for i, col in enumerate(df.columns):
        if '环信息' in str(col):
            ring_col = col
            break
    
    hybrid_col = None
    for i, col in enumerate(df.columns):
        if '杂合信息' in str(col):
            hybrid_col = col
            break
    
    check_col = None
    for i, col in enumerate(df.columns):
        if '翻译校验' in str(col):
            check_col = col
            break
    
    segment_cols = []
    if hybrid_col:
        for col in df.columns:
            if re.search(r'第[一二三四五六七八九十]+区段', str(col)):
                segment_cols.append(col)
        
        def get_segment_num(col_name: str) -> int:
            match = chinese_num_pattern.search(str(col_name))
            if match:
                chinese_num = match.group(1)
                num_map = {'一':1,'二':2,'三':3,'四':4,'五':5,
                          '六':6,'七':7,'八':8,'九':9,'十':10}
                return num_map.get(chinese_num, 0)
            return 0
        
        segment_cols = sorted(segment_cols, key=get_segment_num)
    
    freetext_cols = sorted(
        [col for col in df.columns if str(col).startswith('freetext')], 
        key=lambda x: (len(str(x)), str(x))
    )
    
    sequences: List[Dict[str, Any]] = []
    for row_idx, row in df.iterrows():
        seq = row[seq_col]
        raw_moltype = row[moltype_col] if moltype_col else None
        organism = row[organism_col] if organism_col else 'synthetic construct'
        qual_moltype = row[qual_moltype_col] if qual_moltype_col else None
        check_ref = str(row[check_col]).strip() if check_col and pd.notna(row[check_col]) else None
        
        if not isinstance(seq, str):
            seq = str(seq) if pd.notna(seq) else ""
        
        ring_infos: List[Dict[str, Any]] = []
        if raw_moltype and str(raw_moltype).upper() == "AA" and ring_col is not None and pd.notna(row[ring_col]):
            ring_text = str(row[ring_col])
            for item in re.split(r'[；;]', ring_text):
                match = ring_pattern.search(item.strip())
                if match:
                    ring_infos.append({
                        'start': int(match.group(1)),
                        'end': int(match.group(2)),
                        'note': match.group(3).strip()
                    })
        
        hybrid_segments: List[Dict[str, Any]] = []
        if raw_moltype and str(raw_moltype).upper() == "DNA" and hybrid_col and pd.notna(row[hybrid_col]):
            hybrid_value = str(row[hybrid_col]).strip()
            if hybrid_value.lower() == '是':
                if not segment_cols:
                    raise ValueError(f"第{row_idx+1}行标记为杂合DNA但未找到区段定义列")
                
                for seg_col in segment_cols:
                    if pd.notna(row[seg_col]):
                        seg_str = str(row[seg_col]).strip()
                        match = (hybrid_segment_pattern1.match(seg_str) or
                                 hybrid_segment_pattern2.match(seg_str) or
                                 hybrid_segment_pattern3.match(seg_str))

                        if match:
                            seg_type = match.group(match.lastindex)
                            start = int(match.group(1))
                            # pattern3 (单碱基) 只有2组，start即end
                            if match.lastindex >= 3:
                                end = int(match.group(2))
                            else:
                                end = start
                            
                            if start <= 0:
                                raise ValueError(f"第{row_idx+1}行区段起始位置必须大于0")
                            if start > end:
                                raise ValueError(f"第{row_idx+1}行区段起始位置{start}不能大于结束位置{end}")
                            
                            hybrid_segments.append({
                                'start': start,
                                'end': end,
                                'type': seg_type
                            })
        
        freetexts: List[str] = []
        for ft_col in freetext_cols:
            if pd.notna(row[ft_col]):
                freetexts.append(str(row[ft_col]))

        sequences.append({
            'sequence': seq,
            'moltype': raw_moltype,
            'organism': organism,
            'qual_moltype': qual_moltype,
            'check_ref': check_ref,
            'ring_infos': ring_infos,
            'hybrid_segments': hybrid_segments,
            'freetexts': freetexts,
            'line_number': row_idx + 2,
            'parsed_seq_data': None  # 初始为None，由xml_generator在需要时解析
        })
    
    logger.info(f"Read {len(sequences)} sequences from Excel")
    return sequences


def print_sequence_info(sequences: List[Dict[str, Any]]) -> None:
    """
    打印序列的基本信息到日志。

    Args:
        sequences: 序列字典列表
    """
    logger.info(f"总共 {len(sequences)} 条序列")

    # 统计各分子类型数量
    type_counts = {'DNA': 0, 'RNA': 0, 'AA': 0, 'OTHER': 0}
    for seq in sequences:
        moltype = (seq.get('moltype') or 'RNA').upper()
        if moltype in type_counts:
            type_counts[moltype] += 1
        else:
            type_counts['OTHER'] += 1

    logger.info(f"分子类型分布: DNA={type_counts['DNA']}, RNA={type_counts['RNA']}, AA={type_counts['AA']}, OTHER={type_counts['OTHER']}")


def get_sequence_summary(
    sequences: List[Dict[str, Any]],
    expert_settings: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    生成序列摘要信息。

    Args:
        sequences: 序列字典列表
        expert_settings: 专家模式设置（当前未使用，保留参数以兼容）

    Returns:
        包含以下键的字典:
        - total_count: 总序列数
        - type_counts: 各分子类型的数量统计
        - details: 每条序列的详细信息列表
    """
    # 统计各分子类型数量
    type_counts = {'DNA': 0, 'RNA': 0, 'AA': 0}

    # 生成每条序列的详细信息
    details = []
    for idx, seq_dict in enumerate(sequences, start=1):
        raw_sequence = seq_dict.get('sequence', '')
        moltype = seq_dict.get('moltype') or 'RNA'
        line_number = seq_dict.get('line_number', idx + 1)

        # 解析序列以获取详细的修饰信息
        try:
            naked_seq, modifications, special_positions, raw_moltype, has_degenerate_bases, ligand_removed = parse_sequence(
                raw_sequence, moltype, line_number
            )
        except Exception as e:
            logger.warning(f"Failed to parse sequence {idx} for summary: {e}")
            naked_seq = raw_sequence
            modifications = []
            special_positions = []
            raw_moltype = moltype
            has_degenerate_bases = False
            ligand_removed = False

        moltype_upper = (raw_moltype or 'RNA').upper()
        if moltype_upper not in type_counts:
            moltype_upper = 'RNA'  # 默认为 RNA

        type_counts[moltype_upper] = type_counts.get(moltype_upper, 0) + 1

        # 计算原始长度和裸序列长度
        original_length = len(raw_sequence)
        naked_length = len(naked_seq)

        # 统计修饰数量
        modification_count = len(modifications)

        # 生成修饰和特殊说明
        notes_parts = []

        # 统计各类修饰符
        mod_counts = {}
        for pos, mod_type, base in modifications:
            if mod_type == 'pv':
                mod_counts['pv'] = mod_counts.get('pv', 0) + 1
            elif mod_type in ('m', 'f', 'e'):
                mod_counts[mod_type] = mod_counts.get(mod_type, 0) + 1
            elif mod_type == 's':
                mod_counts['s'] = mod_counts.get('s', 0) + 1

        # 添加修饰信息
        if mod_counts:
            mod_strs = []

            # 使用配置文件中的默认中文名称
            mod_names = MODIFIER_NAMES_ZH_DEFAULT

            for mod_type, count in sorted(mod_counts.items()):
                mod_name = mod_names.get(mod_type, mod_type)
                mod_strs.append(f"{mod_name}×{count}")
            if mod_strs:
                notes_parts.append(f"修饰: {', '.join(mod_strs)}")

        # 统计简并碱基
        if has_degenerate_bases and moltype_upper in ('DNA', 'RNA'):
            degenerate_counts = {}
            for base in naked_seq:
                if base in DEGENERATE_BASES:
                    degenerate_counts[base] = degenerate_counts.get(base, 0) + 1

            if degenerate_counts:
                degenerate_strs = [f"{base}×{count}" for base, count in sorted(degenerate_counts.items())]
                notes_parts.append(f"简并碱基: {', '.join(degenerate_strs)}")

        # 添加特殊位置信息
        if special_positions:
            notes_parts.append(f"特殊位置: {', '.join(map(str, special_positions))}")

        # 添加配体移除信息
        if ligand_removed:
            notes_parts.append("配体移除: L96")

        # 添加环信息
        ring_infos = seq_dict.get('ring_infos', [])
        if ring_infos:
            ring_strs = []
            for ring_info in ring_infos:
                if isinstance(ring_info, dict):
                    region = ring_info.get('region', '')
                    note = ring_info.get('note', '')
                    if region and note:
                        ring_strs.append(f"{region} {note}")
                    elif region:
                        ring_strs.append(region)
                elif isinstance(ring_info, str):
                    ring_strs.append(ring_info)
            if ring_strs:
                notes_parts.append(f"环: {'; '.join(ring_strs)}")

        # 添加杂交片段信息
        hybrid_segments = seq_dict.get('hybrid_segments', [])
        if hybrid_segments:
            hybrid_strs = []
            for segment in hybrid_segments:
                if isinstance(segment, dict):
                    segment_type = segment.get('type', '')
                    segment_range = segment.get('range', '')
                    if segment_type and segment_range:
                        hybrid_strs.append(f"{segment_type}({segment_range})")
                elif isinstance(segment, str):
                    hybrid_strs.append(segment)
            if hybrid_strs:
                notes_parts.append(f"杂交: {'; '.join(hybrid_strs)}")

        # 添加自由文本信息
        freetexts = seq_dict.get('freetexts', [])
        if freetexts:
            notes_parts.extend([f"备注: {ft}" for ft in freetexts[:3]])  # 最多显示3条

        # 组合所有说明
        modification_special_notes = '; '.join(notes_parts) if notes_parts else ''

        detail = {
            'id': idx,
            'type': moltype_upper,
            'organism': seq_dict.get('organism', 'synthetic construct'),
            'length': original_length,
            'naked_length': naked_length,
            'modification_count': modification_count,
            'has_degenerate_bases': has_degenerate_bases,
            'modification_special_notes': modification_special_notes
        }
        details.append(detail)

    summary = {
        'total_count': len(sequences),
        'type_counts': type_counts,
        'details': details
    }

    return summary


def collect_modifiers(seq: str, start_idx: int) -> Tuple[List[str], int]:
    """
    收集连续的修饰符。
    
    Args:
        seq: 序列字符串
        start_idx: 起始索引
        
    Returns:
        (修饰符列表, 结束索引)
    """
    modifiers: List[str] = []
    while start_idx < len(seq) and seq[start_idx] in MODIFIER_CHARS:
        modifiers.append(seq[start_idx].lower())
        start_idx += 1
    return modifiers, start_idx

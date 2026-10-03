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
from typing import Dict, List, NamedTuple, Optional, Set, Tuple, Any
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

# 单字符修饰符。l = LNA，k = 5-Me-LNA-C（5-甲基锁核酸胞苷）。
# 大小写是区分开的：大写 S/K 是简并碱基，小写 s/k 才是修饰符。
MODIFIER_CHARS = {'m', 'f', 'e', 's', 'pv', 'l', 'k'}

# 需要记录成修饰的修饰符（s 特殊，它描述的是碱基之间的键，见下）
BASE_MODIFIERS = ('m', 'f', 'e', 'l', 'k')

# 糖环修饰符：这些修饰挂在核糖 2' 位上，所以带它们的残基骨架仍是核糖 → RNA；
# 裸残基则是 2'-脱氧核糖 → DNA。杂合序列的区段判定靠这条区分（ST.26 ¶3(g)）。
# 目前与 BASE_MODIFIERS 恰好是同一组，但含义不同，别合并：
# 将来若加入不落在糖环上的修饰符（如只改碱基的），两边就会分叉。
SUGAR_MODIFIERS = ('m', 'f', 'e', 'l', 'k')

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


# 厂商括号标注的名称别名表。键是归一化后的名称（小写、去空格、撇号统一为 '），
# 值是旧格式的修饰符字符。用户常从 Word/PDF 粘贴，全角撇号和大小写变体很常见，
# 所以按"容忍常见变体"匹配；认不出的名称一律报错，不静默丢弃。
BRACKET_MODIFIER_ALIASES = {
    # 2'-MOE —— Annex I 表 2 无此修饰，出 XML 时走 OTHER + note
    "2'-moe": 'e',
    "2'moe": 'e',
    "moe": 'e',
    "2'-o-moe": 'e',
    "2'-o-methoxyethyl": 'e',
    "2'-methoxyethyl": 'e',
    # LNA —— 同样不在表 2 内
    "lna": 'l',
    "lockednucleicacid": 'l',
    # 5-Me-LNA-C —— 糖环是 LNA、碱基是 5-甲基胞苷，表 2 的 m5c 描述不了糖环，仍走 OTHER
    "5-me-lna-c": 'k',
    "5me-lna-c": 'k',
    "5-methyl-lna-c": 'k',
    "5-methyl-lockednucleicacid": 'k',
    # 硫代磷酸酯键
    "ps": 's',
    "s": 's',
    "phosphorothioate": 's',
    "*": 's',
    # 既有修饰符的等价写法
    "2'-ome": 'm',
    "2'-o-methyl": 'm',
    "2'-f": 'f',
    "2'-fluoro": 'f',
}

_BRACKET_GROUP_RE = re.compile(r"([A-Za-z])\[([^\]]*)\]")


def _normalize_modifier_name(name: str) -> str:
    """归一化括号内的修饰名：统一全角撇号、去掉所有空格"""
    return name.replace('’', "'").strip().replace(' ', '').lower()


def convert_bracket_format_to_old(seq: str) -> str:
    """
    将厂商括号标注转换为旧格式。

    厂商格式示例（ASO 常见写法）:
        G[2'-MOE,PS]T[2'-MOE,PS]A[PS]C[LNA,PS]C[5-Me-LNA-C,PS]
    旧格式示例:
        GesTesAsClsCks

    括号内多个修饰名用逗号分隔，顺序无关。末端修饰符后面没有碱基时（如序列
    结尾的 [PS]），照常转出，由 parse_sequence 里既有的「s 后面必须跟碱基」
    规则丢弃 —— 与旧格式的既有行为一致。

    Args:
        seq: 输入序列

    Returns:
        转换为旧格式的序列

    Raises:
        ValueError: 括号标注格式不合法，或出现无法识别的修饰名
    """
    if '[' not in seq and ']' not in seq:
        return seq

    converted: List[str] = []
    pos = 0
    for match in _BRACKET_GROUP_RE.finditer(seq):
        # 括号组之前的内容原样保留（可能是普通碱基）
        converted.append(seq[pos:match.start()])
        base, names = match.group(1), match.group(2)
        converted.append(base)
        for raw_name in names.split(','):
            key = _normalize_modifier_name(raw_name)
            if not key:
                continue
            if key not in BRACKET_MODIFIER_ALIASES:
                raise ValueError(
                    f"无法识别的修饰名 '{raw_name.strip()}'（出现在 '{base}[{names}]' 中）"
                )
            converted.append(BRACKET_MODIFIER_ALIASES[key])
        pos = match.end()
    converted.append(seq[pos:])

    result = ''.join(converted)

    # 还残留括号，说明格式本身就不完整（缺右括号、括号前没有碱基等）。
    # 这种输入不能放过：继续往下解析会得到一条碱基对不上号的序列。
    if '[' in result or ']' in result:
        raise ValueError(
            f"括号标注格式不完整：'{seq}'。正确写法如 G[2'-MOE,PS]T[PS]"
        )

    logger.debug(f"Converted bracket format: {result[:50]}...")
    return result


def _append_modifications(
    modifications: List[Any],
    position: int,
    base_lower: str,
    modifiers: List[str],
    seq: str,
    next_index: int
) -> None:
    """把一批已解析出的修饰符记入 modifications。

    parse_sequence 里有三处消费修饰符的地方（修饰符在碱基前、简并碱基后、
    普通碱基后），逻辑完全相同。抽出来是因为新增修饰符时漏改一处不会报错，
    只会让该位置的修饰静默消失。
    """
    for mod in modifiers:
        if mod in BASE_MODIFIERS:
            modifications.append((position, mod, base_lower))
        elif mod == 's' and next_index < len(seq) and seq[next_index].lower() in 'agcut':
            # 硫代描述的是"当前碱基与下一个碱基之间"的键，所以必须先确认后面
            # 确实还有碱基；没有（如序列末尾的 [PS]）就静默忽略。
            modifications.append((f"{position}^{position + 1}", 's', base_lower))


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
    
    # 先转厂商括号格式，再转新格式。两者互不干扰：convert_new_format_to_old
    # 见序列不以 '(' 开头就早退。
    seq = convert_bracket_format_to_old(seq)
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
                    
                _append_modifications(
                    modifications, current_base_pos, base_char_lower, modifiers, seq, i
                )
            
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
                    
                    _append_modifications(
                        modifications, current_base_pos, base_char_lower, modifiers, seq, i
                    )
            
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
                    
                    _append_modifications(
                        modifications, current_base_pos, base_char_lower, modifiers, seq, i
                    )
            
            elif current_char.upper() == 'N':
                naked_sequence.append(current_char)
                current_base_pos = len(naked_sequence)
                base_char_lower = current_char.lower()
                if moltype in ("DNA", "RNA"):
                    special_positions.append(len(naked_sequence))
                i += 1

                # n 后面同样可以带修饰符（方括号写法 N[PS] 就落在这里）。不消费的话
                # 这些字符会被算到下一个碱基头上，那里又因「后一个字符不是碱基」丢掉，
                # 结果是整串硫代键静默消失。
                if i < seq_len and seq[i] in MODIFIER_CHARS:
                    modifiers = []
                    while i < seq_len and seq[i] in MODIFIER_CHARS:
                        modifiers.append(seq[i].lower())
                        i += 1

                    _append_modifications(
                        modifications, current_base_pos, base_char_lower, modifiers, seq, i
                    )
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

_CHINESE_DIGITS = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
                   '六': 6, '七': 7, '八': 8, '九': 9}


def _chinese_numeral_to_int(numeral: str, col_name: str) -> int:
    """
    把「一」～「九十九」的中文数字转成整数，用于区段列排序。

    认不出时抛错而不是返回 0：之前这里返回 0，「第十一区段」这类列会被静默排到
    最前面，区段顺序错了却不报错，比直接失败难查得多。
    """
    if numeral == '十':
        return 10
    if '十' in numeral:
        tens_part, _, ones_part = numeral.partition('十')
        if tens_part and tens_part not in _CHINESE_DIGITS:
            raise ValueError(f"无法识别的区段列名'{col_name}'：'{tens_part}'不是有效的中文数字")
        if ones_part and ones_part not in _CHINESE_DIGITS:
            raise ValueError(f"无法识别的区段列名'{col_name}'：'{ones_part}'不是有效的中文数字")
        tens = _CHINESE_DIGITS[tens_part] if tens_part else 1
        ones = _CHINESE_DIGITS[ones_part] if ones_part else 0
        return tens * 10 + ones
    if numeral in _CHINESE_DIGITS:
        return _CHINESE_DIGITS[numeral]
    raise ValueError(f"无法识别的区段列名'{col_name}'：'{numeral}'不是有效的中文数字")

# 环状结构匹配
_RING_PATTERN = re.compile(r'region\s*[:：]?\s*(\d+)\.\.(\d+).*note\s*[:：]?\s*(.+)', re.I)

# 杂合段匹配
_HYBRID_SEGMENT_PATTERN1 = re.compile(r'\s*(\d+)\s*\.\.\s*(\d+)\s*(RNA|DNA)\s*', re.IGNORECASE)
_HYBRID_SEGMENT_PATTERN2 = re.compile(r'\s*(\d+)\s*-\s*(\d+)\s*(RNA|DNA)\s*', re.IGNORECASE)
_HYBRID_SEGMENT_PATTERN3 = re.compile(r'\s*(\d+)\s+(RNA|DNA)\s*', re.IGNORECASE)


def _sugared_positions(modifications: List[Tuple[Any, str, str]]) -> Set[int]:
    """
    取出带糖环修饰的残基位置（1 起）。

    只取落在具体位点上的修饰。PS 的位置是 "x^y" 字符串，描述的是碱基之间的键，
    与残基类型无关；pv 是磷酸骨架修饰，同样不改变糖环 —— 两者都靠 isinstance 过滤掉。
    """
    return {
        position for position, mod_type, _base in modifications
        if mod_type in SUGAR_MODIFIERS and isinstance(position, int)
    }


def classify_residues(naked_sequence: str,
                      modifications: List[Tuple[Any, str, str]]) -> Optional[List[str]]:
    """
    逐残基给出化学事实：带糖修饰 → 'RNA'，无糖修饰 → 'DNA'。

    判定依据是糖环（ST.26 ¶3(g) 的骨架定义）：带糖修饰（SUGAR_MODIFIERS）的残基骨架
    是核糖；没有糖修饰的残基骨架是 2'-脱氧核糖。这是 gapmer 化学的直接映射，但**不是**
    ST.26 的明文规定 —— ¶55 的官方例子用的都是未修饰的 u 残基，把 2'-MOE/LNA 这种糖修饰
    残基当作 RNA 段属于推断（见 st26_guide.html 的说明）。

    ⚠️ **返回的 'DNA' 只在方括号厂商写法下才成立，别直接拿它当结论。**
    ST.26 里 atcg 在 RNA 和 DNA 之间写法完全相同，所以在旧格式 ``GmGmUmUfG`` 里，
    那个没有修饰符的 ``G`` 只是「没说」，既可能是真脱氧、也可能是漏写了 ``m``。
    只有方括号写法（``G[2'-MOE,PS]T[PS]``）才把每个残基的修饰显式枚举出来，
    ``T[PS]`` 是「明确说了没有糖修饰」—— 这时 'DNA' 才是正面证据。
    所以判定杂合要调 resolve_hybrid（它按标注格式分路径），**不要**直接调这个函数。

    含简并 n 时返回 None：n 在 ST.26 里表示「其他/未知」核苷酸（¶16），
    把它归成 DNA 或 RNA 都是编造，交给用户手工填区段列更诚实。
    """
    if any(ch.upper() == 'N' for ch in naked_sequence):
        return None

    sugared = _sugared_positions(modifications)
    return [
        'RNA' if index in sugared else 'DNA'
        for index in range(1, len(naked_sequence) + 1)
    ]


def group_residue_segments(classification: List[str]) -> List[Dict[str, Any]]:
    """把逐残基分类压成连续区段 —— 铺满整条序列，无空洞也无重叠。"""
    segments: List[Dict[str, Any]] = []
    segment_start = 1
    for index in range(2, len(classification) + 1):
        if classification[index - 1] != classification[segment_start - 1]:
            segments.append({
                'start': segment_start,
                'end': index - 1,
                'type': classification[segment_start - 1],
            })
            segment_start = index
    segments.append({
        'start': segment_start,
        'end': len(classification),
        'type': classification[segment_start - 1],
    })
    return segments


def is_possible_hybrid(naked_sequence: str,
                       modifications: List[Tuple[Any, str, str]]) -> bool:
    """
    序列是否「很可能是杂合体，但因为有简并 n 而无法自动判定区段」。

    detect_hybrid_segments 遇到 n 会直接放弃，但放弃不代表这条序列没问题 ——
    把 n 摘掉之后若剩下的残基有糖修饰也有裸残基，那它多半就是个杂合体，
    只是边界定不了。这种情况必须提醒用户手工填区段列，否则会静默按纯 DNA/RNA 出。
    """
    if not any(ch.upper() == 'N' for ch in naked_sequence):
        return False

    sugared = _sugared_positions(modifications)
    classified = [
        index in sugared
        for index, char in enumerate(naked_sequence, 1)
        if char.upper() != 'N'
    ]
    return any(classified) and not all(classified)


# ============ 标注格式判定 ============

# 方括号厂商格式：整条序列完全由「碱基[修饰清单]」组成。
_ALL_RESIDUES_BRACKETED_RE = re.compile(r"^(?:[A-Za-z]\[[^\]]*\])+$")


def _strip_non_residue_affixes(seq: str) -> str:
    """剥掉不属于残基的片段，供方括号格式判定使用。

    只剥两种确定无害的：5' 端的 PV/VP 前缀（旧格式里写作裸前缀），以及尾部的
    L96 配体标记（parse_sequence 自己也会剥，见 682-689 行）。
    **不剥 `(X)` 括号组** —— 圆括号写法与方括号混用时 parse_sequence 本来就解析失败，
    把它判成方括号格式只会让流程走向「按化学推断」而不是「报解析错」。
    """
    cleaned = re.sub(r'\s+', '', seq)
    for pattern, _length in PV_PREFIX_PATTERNS:
        if re.match(pattern, cleaned):
            cleaned = re.sub(pattern, '', cleaned, count=1)
            break
    for suffix in ('-L96', 'L96'):
        if cleaned.upper().endswith(suffix):
            cleaned = cleaned[: -len(suffix)]
            break
    return cleaned


def uses_bracket_notation(seq: str) -> bool:
    """序列是否采用方括号厂商写法，且**每个**残基都带修饰清单。

    判定是全或无：``G[2'-MOE,PS]T[PS]A[PS]`` 是，``A[PS]GCTT`` 不是。

    严格是刻意的 —— 这是「不带糖修饰 ⇒ 脱氧核糖」这条推断能成立的前提。方括号写法下
    每个残基的修饰都被显式枚举，``T[PS]`` 是「明确说了没有糖修饰」；而旧格式里的裸残基
    只是「没说」，atcg 在 RNA 和 DNA 之间写法完全相同（见 ST.26 ¶13/¶14），判不出。
    """
    if not seq:
        return False
    return bool(_ALL_RESIDUES_BRACKETED_RE.match(_strip_non_residue_affixes(seq)))


def has_partial_bracket_notation(seq: str) -> bool:
    """含方括号但未通过严格判定 —— 多半是漏给个别残基加了括号。

    这种序列会掉进「按旧格式处理、不做杂合识别」的分支，行为落差很大，
    所以要给用户一句提示，否则会毫无征兆地少掉杂合判定。
    """
    return '[' in seq and not uses_bracket_notation(seq)


# ============ 区段渲染与比对 ============

def _segments_signature(segments: List[Dict[str, Any]]) -> List[Tuple[int, int, str]]:
    """区段的可比指纹：先合并相邻的同类型区段，再取(起点, 终点, 类型)。

    合并这一步是必须的：``1..2RNA / 3..4RNA`` 与 ``1..4RNA`` 说的是同一件事，
    不合并就会把这种等价写法判成「与修饰不一致」而中止转换 —— 那是个误报。
    大小写也在这里归一，用户写 ``rna`` 同样接受。
    """
    merged: List[Tuple[int, int, str]] = []
    for seg in sorted(segments, key=lambda item: item['start']):
        kind = str(seg['type']).upper()
        if merged and merged[-1][2] == kind and merged[-1][1] + 1 == seg['start']:
            merged[-1] = (merged[-1][0], seg['end'], kind)
        else:
            merged.append((seg['start'], seg['end'], kind))
    return merged


def format_hybrid_segments(segments: List[Dict[str, Any]], naked_sequence: str) -> str:
    """把区段列表渲染成给人看的一行，带序列字母 —— 没有字母用户没法核对。"""
    parts = []
    for seg in sorted(segments, key=lambda item: item['start']):
        start, end = seg['start'], seg['end']
        location = str(start) if start == end else f"{start}..{end}"
        residues = naked_sequence[start - 1:end] if end <= len(naked_sequence) else '?'
        parts.append(f"{str(seg['type']).upper()} {location} ({residues})")
    return ' / '.join(parts)


def _short_segment_hint(segments: List[Dict[str, Any]]) -> str:
    """短区段的额外提示。单个未修饰残基更可能是漏写了修饰符，而不是真的脱氧 ——
    这两种情况在序列字符串上完全一样，只能提醒用户自己看。"""
    short = [seg for seg in segments if seg['end'] - seg['start'] + 1 <= 2]
    if not short:
        return ''
    described = '、'.join(
        f"{str(seg['type']).upper()} {seg['start']}..{seg['end']}" if seg['start'] != seg['end']
        else f"{str(seg['type']).upper()} {seg['start']}"
        for seg in short
    )
    return f"（注意：{described} 过短，请确认不是漏写了修饰符）"


def _describe_positions(positions: List[int], limit: int = 6) -> str:
    """把位置列表压成区间渲染，过长时截断 —— 提醒文案不能刷屏。

    100 个残基的序列若逐个位置列出来，提醒面板就没法看了，所以超过 limit 段就
    只列前几段再报总数。
    """
    if not positions:
        return ''
    ordered = sorted(set(positions))
    ranges: List[str] = []
    start = prev = ordered[0]
    for pos in ordered[1:]:
        if pos == prev + 1:
            prev = pos
            continue
        ranges.append(str(start) if start == prev else f"{start}..{prev}")
        start = prev = pos
    ranges.append(str(start) if start == prev else f"{start}..{prev}")

    if len(ranges) > limit:
        return '、'.join(ranges[:limit]) + f" 等共 {len(positions)} 位"
    return '、'.join(ranges)


def _positions_in_segments(segments: List[Dict[str, Any]], kind: str) -> Set[int]:
    """取某类型区段覆盖的所有残基位置（1 起）。区段本身由调用方保证已铺满。"""
    positions: Set[int] = set()
    for seg in segments:
        if str(seg.get('type', '')).upper() == kind:
            positions.update(range(int(seg['start']), int(seg['end']) + 1))
    return positions


# ============ 杂合序列判定 ============

class HybridResolution(NamedTuple):
    """resolve_hybrid 的判定结果。

    moltype:  最终分子类型，已含方括号格式下按 ¶55 的自动改写
    segments: 最终区段列表，空列表表示不是杂合体
    hints:    要告知用户的提示文案，**不带**「第N行：」前缀 —— 提醒面板需要行号、
              概要表格每行自带序号不需要，由两个调用方各自决定是否补前缀
    """
    moltype: str
    segments: List[Dict[str, Any]]
    hints: List[str]


def resolve_hybrid(
    sequence: str,
    moltype: str,
    naked_sequence: str,
    modifications: List[Tuple[Any, str, str]],
    user_segments: Optional[List[Dict[str, Any]]] = None,
    line_number: Optional[int] = None,
) -> HybridResolution:
    """判定一条序列的 DNA/RNA 杂合情况。**这是唯一的判定实现点。**

    xml_generator.generate_xml 和 get_sequence_summary 都调它，这样「概要里显示的
    分子类型」与「实际生成的 XML」必然一致 —— 概要跑在生成之前，两边各算一次的话
    迟早会对不上。

    四条路径（按标注格式 × 用户是否填了区段列分叉）：

    ====================  ============  ==========================================
    格式                  填了区段      行为
    ====================  ============  ==========================================
    方括号（ASO）         是            与化学推断严格比对，不一致 → raise
    方括号（ASO）         否            按化学推断，杂合则自动改写为 DNA + 提示
    旧格式 / 圆括号       是            只查硬矛盾：DNA 段里出现糖修饰 → raise；
                                        RNA 段里出现裸残基 → 按未修饰 RNA 处理 + 提示
    旧格式 / 圆括号       否            不做杂合识别（atcg 看不出），必要时提示
    ====================  ============  ==========================================

    中止只用在「用户明确标注了、且化学上不可能」的情况；「判不出来」一律降级为提示。
    另有一条与格式无关的前置检查：填了区段却只有单一类型 → raise（那不是杂合体）。
    """
    hints: List[str] = []
    prefix = f"第{line_number}行：" if line_number else ""
    segments = list(user_segments or [])

    # 多肽没有 DNA/RNA 区段这回事
    if moltype not in ("DNA", "RNA"):
        return HybridResolution(moltype, [], [])

    bracket = uses_bracket_notation(sequence)
    classification = classify_residues(naked_sequence, modifications)
    sugared = _sugared_positions(modifications)

    if segments:
        # 用户勾了「杂合信息=是」，但填的区段只有一种类型 —— 自相矛盾，不是杂合体。
        # ¶55 的三条强制改写（分子类型→DNA、mol_type→other DNA、organism→synthetic
        # construct）只对「DNA/RNA 混合分子」成立，照着一个纯 RNA 区段集套用会把
        # AmGmCmUm 这种全修饰的纯 RNA 序列写成分子上是 DNA，是实打实的错。
        # 这与「漏修饰」不同：那是判不出来，降级为提示；这是用户自己写的两处标注打架。
        kinds = {str(seg.get('type', '')).upper() for seg in segments}
        if len(kinds) < 2:
            only = '、'.join(sorted(k for k in kinds if k)) or '未知'
            raise ValueError(
                f"{prefix}「杂合信息」填了「是」，但区段只有 {only}："
                f"{format_hybrid_segments(segments, naked_sequence)}，不构成杂合体。"
                f"杂合体必须同时含 DNA 段和 RNA 段，请补上缺失的区段，"
                f"或清空「杂合信息」列"
            )

        if bracket:
            if classification is None:
                hints.append(
                    "序列含简并碱基n，无法用修饰核对所填区段，"
                    "已按填写的区段制作，请自行确认"
                )
            else:
                inferred = group_residue_segments(classification)
                if _segments_signature(segments) != _segments_signature(inferred):
                    raise ValueError(
                        f"{prefix}填写的杂合区段与序列修饰不一致。"
                        f"填写的是 {format_hybrid_segments(segments, naked_sequence)}，"
                        f"按修饰推断为 {format_hybrid_segments(inferred, naked_sequence)}。"
                        f"请修正区段列，或补上序列中遗漏的修饰符号"
                    )
        else:
            # 旧格式判不出「哪个是漏写、哪个是真脱氧」，所以只查化学上不可能的硬矛盾。
            conflict = sorted(_positions_in_segments(segments, 'DNA') & sugared)
            if conflict:
                raise ValueError(
                    f"{prefix}区段标注与序列修饰矛盾：第 {_describe_positions(conflict)} 位"
                    f"标在DNA段内，却带有2'位糖修饰（糖修饰说明该位是核糖）。"
                    f"请修正区段列，或去掉该位置多写的修饰符号"
                )
            unmodified = sorted(_positions_in_segments(segments, 'RNA') - sugared)
            if unmodified:
                hints.append(
                    f"第 {_describe_positions(unmodified)} 位标在RNA段内但没有修饰符号，"
                    f"已按未修饰的RNA残基处理"
                )
        # 有区段就是杂合体，¶55 要求分子类型必须是 DNA —— 与用户填的 DNA/RNA 无关。
        # 这与 generate_xml 里 is_hybrid 分支的改写是同一条规则，两边必须一致。
        return HybridResolution("DNA", segments, hints)

    if bracket:
        if classification is not None and len(set(classification)) > 1:
            segments = group_residue_segments(classification)
            hints.append(
                f"检测到DNA/RNA杂合序列，已按ST.26第55段自动判定："
                f"分子类型\"DNA\"、mol_type\"other DNA\"。"
                f"区段为 {format_hybrid_segments(segments, naked_sequence)}，请核对"
                + _short_segment_hint(segments)
            )
            return HybridResolution("DNA", segments, hints)
        if is_possible_hybrid(naked_sequence, modifications):
            hints.append(
                "序列含简并碱基n且修饰分布不均，可能是DNA/RNA杂合序列，"
                "但因n无法自动判定区段。请手工填写杂合区段列"
            )
        return HybridResolution(moltype, [], hints)

    # 旧格式 + 未填区段：不做杂合识别。atcg 在 RNA 和 DNA 之间写法相同，
    # 裸残基既可能是真脱氧、也可能是漏写了修饰符号，判不出就不猜。
    if has_partial_bracket_notation(sequence):
        hints.append(
            "序列含方括号但并非每个残基都标注了修饰，"
            "已按旧格式处理，不做杂合区段识别"
        )
    if classification is not None and len(set(classification)) > 1:
        unmodified = [index for index, kind in enumerate(classification, 1) if kind == 'DNA']
        hints.append(
            f"第 {_describe_positions(unmodified)} 位没有修饰符号，"
            f"已按未修饰的RNA残基处理；若本意是脱氧核糖，请填写杂合区段列"
        )
    return HybridResolution(moltype, [], hints)


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
                return _chinese_numeral_to_int(match.group(1), col_name)
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
        # 这里不再要求分子类型必须是 DNA。填「杂合信息=是」的用户的意图很清楚，
        # 原先只在 moltype == "DNA" 时才读区段列，导致填 RNA 的行区段被静默丢弃
        # （xml_generator 那边的提醒还会说成「未填写杂合区段信息」，与事实相反）。
        # AA 序列排除在外：多肽没有 DNA/RNA 区段这回事。
        row_moltype = str(raw_moltype).strip().upper() if pd.notna(raw_moltype) else ""
        if row_moltype != "AA" and hybrid_col and pd.notna(row[hybrid_col]):
            hybrid_value = str(row[hybrid_col]).strip()
            if hybrid_value.lower() == '是':
                if not segment_cols:
                    raise ValueError(f"第{row_idx+1}行标记为杂合序列但未找到区段定义列")
                
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


def normalize_moltype(raw_moltype: Any, default: str = 'RNA') -> str:
    """把从 Excel 读来的分子类型归一成大写字符串。

    pandas 读空单元格得到的是 NaN（float），而 NaN 是**真值** —— 直接写
    ``(raw or 'RNA').upper()`` 会抛 ``AttributeError: 'float' object has no
    attribute 'upper'``。所有从表格取分子类型的地方都要走这里。
    """
    if raw_moltype is None or (isinstance(raw_moltype, float) and pd.isna(raw_moltype)):
        return default
    text = str(raw_moltype).strip().upper()
    return text or default


def clean_cell_text(value: Any) -> str:
    """把 Excel 单元格值归一成字符串。

    空单元格经 pandas 读出来是 NaN（float），当成字符串用会在 ``len()``、正则、
    迭代处抛 TypeError —— 归一成空串。与 normalize_moltype 是同一类问题：表格里
    只要有一格是空的，整个概要就不该因此消失。
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ''
    return value if isinstance(value, str) else str(value)


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
        moltype = normalize_moltype(seq.get('moltype'))
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
        raw_sequence = clean_cell_text(seq_dict.get('sequence'))
        moltype = normalize_moltype(seq_dict.get('moltype'))
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

        # 杂合判定走与 generate_xml 完全相同的函数 —— 概要跑在生成之前，两边各算一次
        # 迟早会对不上（比如 ASO 被自动改写成 DNA 后，概要里还显示 RNA）。这里只负责
        # 展示，所以硬矛盾抛的 ValueError 要吞掉：强制点在 generate_xml。
        try:
            resolution = resolve_hybrid(
                raw_sequence, moltype, naked_seq, modifications,
                seq_dict.get('hybrid_segments'), line_number
            )
        except ValueError as e:
            logger.warning(f"Sequence {idx} hybrid resolution failed: {e}")
            resolution = HybridResolution(moltype, [], [])

        moltype_upper = normalize_moltype(resolution.moltype)
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
            elif mod_type in BASE_MODIFIERS:
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

        # 添加杂交片段信息。用 resolve_hybrid 判出的**最终**区段 —— 含自动推断的那部分，
        # 不只是用户手填的。它跑在 generate_xml 之前，但用的是同一个函数，所以对得上。
        if resolution.segments:
            hybrid_strs = []
            for segment in resolution.segments:
                segment_type = str(segment.get('type', '')).upper()
                start, end = segment.get('start'), segment.get('end')
                if segment_type and start is not None and end is not None:
                    segment_range = str(start) if start == end else f"{start}..{end}"
                    hybrid_strs.append(f"{segment_type}({segment_range})")
            if hybrid_strs:
                notes_parts.append(f"杂交: {'; '.join(hybrid_strs)}")

        # 判定过程中的提示（自动改写为DNA、按未修饰RNA处理、疑似方括号未标全等）。
        # 同一批文案也会进 generate_xml 的提醒面板，两处口径一致。
        notes_parts.extend(resolution.hints)

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

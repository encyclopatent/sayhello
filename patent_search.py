"""
专利序列检索模块 - 通过NCBI BLAST API搜索专利库并提取公开号

流程：
1. POST序列到 NCBI BLAST（专利申请专用库）
2. 轮询等待结果
3. 解析XML，提取Hit信息
4. 从Hit描述中抽提专利号
"""

import re
import time
import logging
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import quote, urlencode

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

logger = logging.getLogger(__name__)

# NCBI BLAST API 端点
BLAST_URL = "https://blast.ncbi.nlm.nih.gov/blast/Blast.cgi"

# 专利号匹配模式
PATENT_PATTERNS = [
    # US Patent: US1234567, US2020123456A1, US-2020-123456-A1
    r'US[\s\-]*\d[\d,\-A-Za-z]*',
    # WO: WO2020123456, WO2020/123456
    r'WO[\s\-]*\d[\d/\-A-Za-z]*',
    # EP: EP1234567, EP1234567A1
    r'EP[\s\-]*\d[\d\-A-Za-z]*',
    # CN: CN123456789A, CN2020123456
    r'CN[\s\-]*\d[\d\-A-Za-z]*',
    # JP: JP2020123456
    r'JP[\s\-]*\d[\d\-A-Za-z]*',
    # KR, AU, CA, etc
    r'(?:KR|AU|CA|DE|FR|GB|IN|RU|SG)\d[\d\-A-Za-z]*',
]

# 更宽松的专利号（含Patent关键词的行中提取）
PATENT_KW_PATTERN = re.compile(
    r'(?:patent|patent\s*application|专利|特许|特許|公开号)'
    r'[\s:;#]*'
    r'([A-Z]{2,4}[\s\-]*\d[\d,\-A-Za-z\.]*)',
    re.IGNORECASE
)

# 括号内专利号
PAREN_PATTERN = re.compile(r'\(([A-Z]{2,4}[\s\-]*\d[\d\-A-Za-z]*)\)')


def _normalize_patent_id(raw: str) -> str:
    """规范化专利号：去除空格和连接符，统一格式"""
    pid = raw.strip().rstrip('.,;:')
    # 移除空格
    pid = re.sub(r'\s+', '', pid)
    # 移除连接符
    pid = pid.replace('-', '')
    # 大写
    pid = pid.upper()
    return pid


def extract_patent_numbers(text: str) -> List[str]:
    """
    从文本中提取专利号。

    Args:
        text: BLAST检索结果中的Hit描述文本

    Returns:
        规范化后的专利号列表
    """
    found = set()

    # 方法1: 从"Patent:"关键词行提取
    for match in PATENT_KW_PATTERN.finditer(text):
        pid = _normalize_patent_id(match.group(1))
        if pid and len(pid) >= 4:
            found.add(pid)

    # 方法2: 括号内的专利号
    for match in PAREN_PATTERN.finditer(text):
        pid = _normalize_patent_id(match.group(1))
        if pid and len(pid) >= 4:
            found.add(pid)

    # 方法3: 正则模式匹配
    for pattern in PATENT_PATTERNS:
        for match in re.finditer(pattern, text):
            pid = _normalize_patent_id(match.group(0))
            if pid and len(pid) >= 4:
                found.add(pid)

    return sorted(found)


def _is_patent_hit(hit_def: str, hit_acc: str) -> bool:
    """判断BLAST命中是否与专利相关"""
    combined = f"{hit_def} {hit_acc}".upper()
    keywords = ['PATENT', 'PUBLIC', 'APPLICATION', 'USPTO', 'EPO', 'PCT',
                'WO', 'PUBLICATION', 'PAT', 'SEQ ID', 'SEQUENCE LISTING']
    return any(kw in combined for kw in keywords)


def lookup_patent_numbers(accessions: List[str]) -> Dict[str, List[str]]:
    """
    通过NCBI E-utilities查询与核酸序列相关的专利公开号。

    Args:
        accessions: NCBI accession列表

    Returns:
        {accession: [patent_numbers]}
    """
    if not accessions or not HAS_REQUESTS:
        return {}

    result: Dict[str, List[str]] = {}
    ELINK_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"

    # 每批最多处理20个
    batch_size = 20
    for start in range(0, len(accessions), batch_size):
        batch = accessions[start:start + batch_size]
        try:
            params = {
                'dbfrom': 'nucleotide',
                'db': 'pubmed',
                'id': ','.join(batch),
                'retmode': 'json',
            }
            resp = requests.get(ELINK_URL, params=params,
                              headers={'User-Agent': 'Mozilla/5.0'},
                              timeout=15)
            if resp.status_code != 200:
                continue

            data = resp.json()
            linksets = data.get('linksets', [])

            for ls in linksets:
                ids = ls.get('ids', [])
                links = ls.get('linksetsubs', [])
                # 查找 patent 相关链接
                for link_sub in links:
                    if 'patent' in str(link_sub.get('name', '')).lower():
                        for uid in link_sub.get('links', []):
                            # 提取专利ID
                            pass  # pubmed ID不是专利号，需要进一步查询

                # 直接提取pubmed ID并转换为专利号
                for ls in linksets:
                    for link_sub in ls.get('linksetsubs', []):
                        if 'patent' in str(link_sub.get('name', '')).lower():
                            result.setdefault(','.join(ids), []).extend(
                                [str(uid) for uid in link_sub.get('links', [])])

        except Exception as e:
            logger.warning(f"elink lookup failed for batch: {e}")

    return result


def submit_blast(
    sequence: str,
    program: str = 'blastn',
    hitlist_size: int = 50,
    expect: float = 10.0,
) -> Tuple[Optional[str], Optional[str]]:
    """
    提交BLAST检索到NCBI专利库。

    Args:
        sequence: 查询序列
        program: blastn(核酸) 或 blastp(蛋白)
        hitlist_size: 返回最大命中数
        expect: E-value阈值

    Returns:
        (RID, RTOE) 或 (None, error_msg)
    """
    if not HAS_REQUESTS:
        return None, "缺少 requests 库，请执行: pip install requests"

    # 自动检测序列类型
    seq_upper = sequence.upper().strip()
    has_protein_chars = any(c in seq_upper for c in 'DEFHIKLMNPQRSUVWY')
    has_T = 'T' in seq_upper
    has_U = 'U' in seq_upper

    if program == 'auto':
        if has_U:
            program = 'blastn'
        elif has_T and not has_protein_chars:
            program = 'blastn'
        else:
            program = 'blastp'

    database = 'nr'
    if program == 'blastn':
        database = 'nt'

    params = {
        'CMD': 'Put',
        'PROGRAM': program,
        'DATABASE': database,
        'QUERY': sequence,
        'HITLIST_SIZE': hitlist_size,
        'EXPECT': expect,
        'FORMAT_TYPE': 'XML',
        'FILTER': 'L',
    }

    logger.info(f"Submitting BLAST to NCBI: program={program}, db={database}, seq_len={len(seq_upper)}")

    try:
        resp = requests.post(
            BLAST_URL,
            data=params,
            headers={'User-Agent': 'Mozilla/5.0'},
            timeout=30,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        return None, f"提交BLAST失败: {str(e)}"

    # 从HTML响应中提取RID和RTOE
    text = resp.text
    rid_match = re.search(r'RID\s*=\s*["\']?([A-Z0-9\-]+)["\']?', text)
    rtoe_match = re.search(r'RTOE\s*=\s*["\']?(\d+)["\']?', text)

    if not rid_match:
        return None, "未能获取到RID，BLAST可能被限流"

    rid = rid_match.group(1)
    rtoe = int(rtoe_match.group(1)) if rtoe_match else 30
    logger.info(f"BLAST submitted: RID={rid}, estimated_time={rtoe}s")

    return rid, None


def poll_blast(rid: str, max_wait: int = 300, poll_interval: int = 5) -> Tuple[Optional[str], Optional[str]]:
    """
    轮询BLAST结果直至完成。

    Args:
        rid: NCBI BLAST的Request ID
        max_wait: 最大等待时间（秒）
        poll_interval: 轮询间隔（秒）

    Returns:
        (XML结果字符串, None) 或 (None, error_msg)
    """
    if not HAS_REQUESTS:
        return None, "缺少 requests 库"

    # 先用FORMAT_TYPE=XML请求
    url_with_xml = f"{BLAST_URL}?CMD=Get&RID={rid}&FORMAT_TYPE=XML"

    start = time.time()
    while time.time() - start < max_wait:
        try:
            resp = requests.get(
                url_with_xml,
                headers={'User-Agent': 'Mozilla/5.0'},
                timeout=30,
            )
            resp.raise_for_status()
            text = resp.text

            # 情况1: XML结果已就绪（无Status行，直接返回BlastOutput）
            if '<BlastOutput>' in text or text.strip().startswith('<?xml'):
                logger.info(f"BLAST results ready (XML direct), RID={rid}")
                return text, None

            # 情况2: 有Status行，检查状态
            if 'Status=' in text:
                status_match = re.search(r'Status\s*=\s*(\w+)', text)
                if status_match:
                    status = status_match.group(1).upper()
                    logger.debug(f"BLAST status: {status}")
                    if status in ('READY', 'DONE'):
                        # 再次请求XML格式
                        try:
                            xml_resp = requests.get(
                                url_with_xml,
                                headers={'User-Agent': 'Mozilla/5.0'},
                                timeout=30,
                            )
                            if xml_resp.ok and ('<BlastOutput>' in xml_resp.text):
                                return xml_resp.text, None
                        except Exception:
                            pass
                        return text, None
                    elif status == 'UNKNOWN':
                        return None, "BLAST RID已过期，请重新提交"
                    # WAITING → 继续

        except requests.RequestException as e:
            logger.warning(f"Poll BLAST error: {e}")

        time.sleep(poll_interval)

    return None, f"BLAST等待超时（{max_wait}s），RID={rid}，稍后手动查询"


def parse_blast_xml(xml_text: str) -> Dict[str, Any]:
    """
    解析BLAST XML结果，提取Hit信息和专利号。

    Args:
        xml_text: BLAST返回的XML字符串

    Returns:
        {
            'hits': [...],
            'patent_numbers': [...],  # 去重合并的专利号列表
            'statistics': {...}
        }
    """
    result: Dict[str, Any] = {
        'hits': [],
        'patent_numbers': [],
        'statistics': {
            'total_hits': 0,
            'query_length': 0,
            'program': '',
            'database': '',
        },
    }

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        logger.error(f"XML parse error: {e}")
        return result

    # root is <BlastOutput> directly
    if root.tag != 'BlastOutput':
        logger.error(f"Unexpected root tag: {root.tag}")
        return result

    result['statistics']['program'] = _safe_xml(root, 'BlastOutput_program')
    result['statistics']['database'] = _safe_xml(root, 'BlastOutput_db')

    # Iterations
    for iteration in root.iter('Iteration'):
        iter_hits = iteration.find('Iteration_hits')
        if iter_hits is None:
            continue

        for hit in iter_hits.findall('Hit'):
            hit_id = _safe_xml(hit, 'Hit_id')
            hit_def = _safe_xml(hit, 'Hit_def')
            hit_accession = _safe_xml(hit, 'Hit_accession')
            hit_len_text = _safe_xml(hit, 'Hit_len')
            hit_len = int(hit_len_text) if hit_len_text and hit_len_text.isdigit() else 0

            # 拼接完整描述
            full_desc = f"{hit_def} [{hit_accession}]"

            # 提取专利号
            patent_nums = extract_patent_numbers(full_desc)
            # 从 Hit 描述中也提取
            patent_nums.extend(extract_patent_numbers(hit_def))
            patent_nums.extend(extract_patent_numbers(hit_id))
            patent_numbers = sorted(set(patent_nums))

            # 获取第一个 HSP
            best_hsp = None
            hsps = hit.findall('Hit_hsps/Hsp')
            if hsps:
                hsp = hsps[0]
                best_hsp = {
                    'score': int(_safe_xml(hsp, 'Hsp_score') or 0),
                    'evalue': _safe_xml(hsp, 'Hsp_evalue'),
                    'identity': int(_safe_xml(hsp, 'Hsp_identity') or 0),
                    'positive': int(_safe_xml(hsp, 'Hsp_positive') or 0),
                    'gaps': int(_safe_xml(hsp, 'Hsp_gaps') or 0),
                    'align_len': int(_safe_xml(hsp, 'Hsp_align-len') or 0),
                    'query_from': int(_safe_xml(hsp, 'Hsp_query-from') or 0),
                    'query_to': int(_safe_xml(hsp, 'Hsp_query-to') or 0),
                    'hit_from': int(_safe_xml(hsp, 'Hsp_hit-from') or 0),
                    'hit_to': int(_safe_xml(hsp, 'Hsp_hit-to') or 0),
                }
                if best_hsp['align_len'] > 0:
                    best_hsp['identity_pct'] = round(
                        best_hsp['identity'] / best_hsp['align_len'] * 100, 2
                    )
                else:
                    best_hsp['identity_pct'] = 0.0

            hit_entry = {
                'id': hit_id,
                'accession': hit_accession,
                'definition': hit_def,
                'length': hit_len,
                'patent_numbers': patent_numbers,
                'best_hsp': best_hsp,
            }
            result['hits'].append(hit_entry)

    # 计算统计
    result['statistics']['total_hits'] = len(result['hits'])

    # 去重合并所有专利号
    all_patents = set()
    for hit_entry in result['hits']:
        for pn in hit_entry.get('patent_numbers', []):
            all_patents.add(pn)

    # 检查 query 长度
    qlen_el = root.find('.//Parameters//Parameters_query-len')
    if qlen_el is not None and qlen_el.text:
        result['statistics']['query_length'] = int(qlen_el.text)

    result['patent_numbers'] = sorted(all_patents)

    # 按score排序
    result['hits'].sort(
        key=lambda h: (h.get('best_hsp') or {}).get('score', 0),
        reverse=True,
    )

    logger.info(f"Parsed {len(result['hits'])} hits, found {len(all_patents)} unique patent numbers")
    return result


def search_patents(
    sequence: str,
    program: str = 'auto',
    hitlist_size: int = 50,
    expect: float = 10.0,
    max_wait: int = 300,
) -> Dict[str, Any]:
    """
    一站式专利序列检索：提交 → 等待 → 解析 → 提取专利号。

    Args:
        sequence: 查询序列
        program: blastn / blastp / auto
        hitlist_size: 最大命中数
        expect: E-value阈值
        max_wait: 最大等待时间（秒）

    Returns:
        {
            'status': 'success' | 'error',
            'message': str,
            'hits': [...],
            'patent_numbers': [...],
            'statistics': {...},
            'rid': str,  # RID供后续手动查询
        }
    """
    result: Dict[str, Any] = {
        'status': 'error',
        'message': '',
        'hits': [],
        'patent_numbers': [],
        'statistics': {},
        'rid': '',
    }

    # Step 1: Submit
    rid, error = submit_blast(sequence, program, hitlist_size, expect)
    if error:
        result['message'] = error
        return result

    result['rid'] = rid

    # Step 2: Poll
    xml_text, error = poll_blast(rid, max_wait=max_wait)
    if error:
        result['message'] = error
        return result

    # Step 3: Parse
    parsed = parse_blast_xml(xml_text)
    result['hits'] = parsed['hits']
    result['patent_numbers'] = parsed['patent_numbers']
    result['statistics'] = parsed['statistics']
    result['status'] = 'success'
    result['message'] = f"检索完成，发现 {parsed['statistics']['total_hits']} 条命中"

    return result


def search_patents_from_excel(
    file_path: str,
    program: str = 'auto',
    hitlist_size: int = 50,
) -> List[Dict[str, Any]]:
    """
    从Excel批量检索专利序列。

    Excel需包含"序列"列，每行一条序列。
    """
    import pandas as pd

    df = pd.read_excel(file_path, engine='openpyxl')
    df.dropna(how='all', inplace=True)

    col_names = [str(col).lower() for col in df.columns]

    seq_col = None
    name_col = None
    for i, col in enumerate(col_names):
        if any(kw in col for kw in ['序列', 'sequence', 'seq']):
            seq_col = df.columns[i]
        if any(kw in col for kw in ['名称', 'name', '序列名']):
            name_col = df.columns[i]

    if not seq_col:
        seq_col = df.columns[0]

    results = []
    for idx, row in df.iterrows():
        seq = str(row[seq_col]) if pd.notna(row[seq_col]) else ''
        if not seq:
            continue
        name = str(row[name_col]) if name_col and pd.notna(row[name_col]) else f'序列{idx + 1}'
        logger.info(f"Searching patent [{idx + 1}/{len(df)}]: {name}")

        result = search_patents(seq, program=program, hitlist_size=hitlist_size)
        result['name'] = name
        result['index'] = idx + 1
        results.append(result)

    return results


def _safe_xml(parent: ET.Element, tag: str) -> str:
    """安全读取XML子元素文本"""
    el = parent.find(tag)
    if el is not None and el.text:
        return el.text.strip()
    return ''

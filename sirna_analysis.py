import pandas as pd
from Bio.Seq import Seq
from Bio.SeqIO import parse
from Bio.Blast import NCBIWWW
from Bio.Blast import NCBIXML
import os
import re
from datetime import datetime
from collections import OrderedDict
import time


def sanitize_string_content(text: str) -> str:
    """
    净化字符串内容，移除特殊字符和中文字符，防止服务器错误

    参考ST26模块的sanitize_filename和split_chinese_english处理方式

    参数:
        text: 待净化的字符串

    返回:
        净化后的字符串，只保留字母、数字和基本标点
    """
    if not isinstance(text, str):
        text = str(text) if text is not None else ""

    # 移除中文字符（Unicode范围：\u4e00-\u9fff）
    # 移除特殊字符，只保留字母、数字、空格和基本标点
    cleaned = re.sub(r'[^\w\s\-\.\,\(\)]', '', text)

    # 移除多余空白
    cleaned = ' '.join(cleaned.split())

    return cleaned.strip()


def find_max_continuous(query, target, max_mismatch=1):
    """
    滑动窗口寻找最长连续匹配
    允许最多max_mismatch个错配
    """
    max_len = best_start = 0
    q_len, t_len = len(query), len(target)
    
    for i in range(t_len - q_len + 1):
        curr_len = mismatches = 0
        
        for j in range(q_len):
            if i + j >= t_len:
                break
                
            if query[j] == target[i+j]:
                curr_len += 1
            else:
                mismatches += 1
                if mismatches > max_mismatch:
                    break
                curr_len += 1
            
            if curr_len > max_len:
                max_len = curr_len
                best_start = i
    
    return best_start, best_start + max_len



def count_mismatches(seq1, seq2):
    """计算两个序列之间的错配数"""
    if len(seq1) != len(seq2):
        return max(len(seq1), len(seq2))
    return sum(1 for a, b in zip(seq1, seq2) if a != b)







def check_sirna_match(query, target, max_mismatch=1):
    """检测siRNA匹配类型"""
    if not query or not target:
        return "无效序列", "N/A"

    query_len = len(query)
    target_len = len(target)
    
    # 目标序列太短，无法匹配
    if target_len < 18:
        return "非siRNA", "N/A"
    
    # 首先检查原始序列（18-22bp）是否匹配
    if 18 <= query_len <= 22:
        # 使用快速的滑动窗口算法进行匹配
        # 正向链检测
        start, end = find_max_continuous(query, target, max_mismatch)
        match_length = end - start
        
        if match_length >= 18:  # siRNA通常18-21bp
            return "正义链", f"{start}-{end} ({match_length}bp)"

        # 反向互补链检测
        rc_query = str(Seq(query).reverse_complement())
        rc_start, rc_end = find_max_continuous(rc_query, target, max_mismatch)
        rc_match_length = rc_end - rc_start
        
        if rc_match_length >= 18:
            return "反义链", f"{rc_start}-{rc_end} ({rc_match_length}bp)"

    # 如果原始序列匹配失败，尝试从两端各去除2个碱基后重新匹配
    if query_len >= 22:  # 确保截短后至少有18bp
        # 两端各截短2个碱基
        trimmed_query = query[2:-2]
        trimmed_query_len = len(trimmed_query)
        
        if trimmed_query_len >= 18:
            # 正向链检测（截短后）
            trimmed_start, trimmed_end = find_max_continuous(trimmed_query, target, max_mismatch)
            trimmed_match_length = trimmed_end - trimmed_start
            
            if trimmed_match_length >= 18:
                return "正义链", f"{trimmed_start}-{trimmed_end} ({trimmed_match_length}bp) [存在突出端]"

            # 反向互补链检测（截短后）
            trimmed_rc_query = str(Seq(trimmed_query).reverse_complement())
            trimmed_rc_start, trimmed_rc_end = find_max_continuous(trimmed_rc_query, target, max_mismatch)
            trimmed_rc_match_length = trimmed_rc_end - trimmed_rc_start
            
            if trimmed_rc_match_length >= 18:
                return "反义链", f"{trimmed_rc_start}-{trimmed_rc_end} ({trimmed_rc_match_length}bp) [存在突出端]"

    return "非siRNA", "N/A"


def blastn_search_ncbi(target_sequence, blast_type="blastn", database="nt", evalue=0.01, max_hits=5):
    """
    使用NCBI BLAST网络服务检索靶序列
    
    参数:
        target_sequence: 靶序列
        blast_type: BLAST类型 (默认: blastn)
        database: 数据库名称 (默认: nt - nucleotide collection)
        evalue: E-value阈值 (默认: 0.01)
        max_hits: 最大返回结果数 (默认: 5)
        
    返回:
        blast_results: BLAST匹配结果列表，每个结果包含NCBI ID、描述、匹配长度、一致性等信息
    """
    if not target_sequence:
        return []
    
    try:
        # 执行BLAST搜索
        print(f"正在执行BLAST搜索...")
        result_handle = NCBIWWW.qblast(
            program=blast_type,
            database=database,
            sequence=target_sequence,
            expect=evalue,
            hitlist_size=max_hits
        )
        
        # 解析BLAST结果
        blast_records = NCBIXML.parse(result_handle)
        blast_results = []
        
        for blast_record in blast_records:
            for alignment in blast_record.alignments:
                for hsp in alignment.hsps:
                    # 提取NCBI ID (GenBank accession)
                    accession = alignment.accession
                    
                    # 提取描述信息
                    description = alignment.title
                    
                    # 构建结果字典
                    result = {
                        "ncbi_id": accession,
                        "description": description,
                        "match_length": hsp.align_length,
                        "identity": hsp.identities,
                        "identity_percent": (hsp.identities / hsp.align_length) * 100,
                        "evalue": hsp.expect,
                        "query_start": hsp.query_start,
                        "query_end": hsp.query_end,
                        "subject_start": hsp.sbjct_start,
                        "subject_end": hsp.sbjct_end,
                        "query_sequence": hsp.query,
                        "subject_sequence": hsp.sbjct,
                        "alignment_sequence": hsp.match
                    }
                    blast_results.append(result)
        
        return blast_results
        
    except Exception as e:
        print(f"BLAST搜索失败: {e}")
        return []
    finally:
        try:
            result_handle.close()
        except:
            pass


def generate_alignment_details(query_seq, target_seq, strand_type, max_mismatch=1):
    """
    生成序列比对的详细信息

    参数:
        query_seq: 查询序列
        target_seq: 靶序列
        strand_type: 链类型（"正义链" 或 "反义链"）
        max_mismatch: 最大允许错配数

    返回:
        alignment_details: 包含比对详情的字典
    """
    try:
        # 根据链类型确定要比对的序列
        if strand_type == "反义链":
            query_aligned = str(Seq(query_seq).reverse_complement())
        else:
            query_aligned = query_seq

        # 在靶序列中查找最佳匹配位置
        start, end = find_max_continuous(query_aligned, target_seq, max_mismatch)

        # 提取靶序列中的匹配片段
        if end > start:
            target_matched = target_seq[start:end]
        else:
            return None

        # 确保长度一致
        min_len = min(len(query_aligned), len(target_matched))
        query_aligned = query_aligned[:min_len]
        target_matched = target_matched[:min_len]

        # 生成比对字符串
        alignment_symbols = []
        match_count = 0
        mismatch_positions = []

        for i, (q, t) in enumerate(zip(query_aligned, target_matched)):
            if q == t:
                alignment_symbols.append('|')  # 匹配
                match_count += 1
            else:
                alignment_symbols.append('×')  # 错配
                mismatch_positions.append(i + 1)  # 1-based position

        # 计算匹配百分比
        match_percent = (match_count / min_len * 100) if min_len > 0 else 0

        return {
            'query_aligned': query_aligned,
            'target_aligned': target_matched,
            'alignment_symbols': ''.join(alignment_symbols),
            'match_count': match_count,
            'mismatch_count': min_len - match_count,
            'mismatch_positions': mismatch_positions,
            'match_percent': round(match_percent, 2),
            'alignment_length': min_len,
            'target_start': start,
            'target_end': end
        }

    except Exception:
        return None


def find_best_match(query_pos, literature_results, query_strand_type=None):
    """
    找到最佳匹配的文献序列

    参数:
        query_pos: 查询序列的匹配位置
        literature_results: 文献序列匹配结果列表
        query_strand_type: 查询序列的链类型（"正义链" 或 "反义链"）

    返回:
        best_match: 最佳匹配的文献序列结果，优先匹配相同链类型
    """
    if not query_pos or query_pos == "N/A" or not literature_results:
        return None

    try:
        # 解析位置字符串 (格式: "start-end (length bp)")
        q_pos = query_pos.split('(')[0].strip()
        q_start, q_end = map(int, q_pos.split('-'))
        q_len = q_end - q_start

        best_score = -1
        best_match = None

        # 分为两组：相同链类型和不同链类型
        same_strand_matches = []
        different_strand_matches = []

        for result in literature_results:
            lit_pos = result['匹配位置'].split('(')[0].strip()
            l_start, l_end = map(int, lit_pos.split('-'))

            # 计算重叠分数
            overlap_start = max(q_start, l_start)
            overlap_end = min(q_end, l_end)
            overlap_len = max(0, overlap_end - overlap_start)

            # 计算匹配质量分数
            score = overlap_len - abs(q_start - l_start) * 0.1

            # 根据链类型分组
            if query_strand_type and result.get('链类型'):
                if query_strand_type == result.get('链类型'):
                    same_strand_matches.append((score, result))
                else:
                    different_strand_matches.append((score, result))
            else:
                # 如果没有链类型信息，都放入相同链类型组
                same_strand_matches.append((score, result))

        # 优先从相同链类型中找最佳匹配
        for score, result in same_strand_matches:
            if score > best_score:
                best_score = score
                best_match = result

        # 如果相同链类型没有找到好的匹配，才考虑不同链类型
        if best_score < 0.8 * q_len:
            for score, result in different_strand_matches:
                if score > best_score:
                    best_score = score
                    best_match = result

        return best_match if best_score >= 0.8 * q_len else None

    except Exception:
        return None



def parse_sequences_from_excel(excel_path, preview_mode=False):
    """解析Excel文件中的序列"""
    try:
        df = pd.read_excel(excel_path, engine='openpyxl')
        # 添加dropna操作，解决幽灵数据问题
        df.dropna(how='all', inplace=True)
        
        # 验证列数
        if len(df.columns) < 2:
            raise ValueError("Excel必须包含至少两列数据")
        
        # 获取序列 - 对列名也进行净化，防止特殊字符导致错误
        query_col = df.columns[0]
        target_col = df.columns[1]

        # 标准化处理 - 增强版，处理特殊字符和中文字符
        # 标准化处理 - 只保留有效的核酸字符（ATCGU），不破坏序列
        def sanitize_seq(seq):
            if not isinstance(seq, str):
                seq = str(seq) if seq is not None else ""

            # 只保留有效的核酸字符（ATCGU），不破坏连续性
            valid_chars = {'A', 'T', 'C', 'G', 'U'}
            filtered = [c.upper() for c in seq if c.upper() in valid_chars]
            return ''.join(filtered).replace('U', 'T')

        # 解析查询序列 - 只转大写和过滤有效字符，不过度净化
        query_sequences = (
            df[query_col]
            .dropna()
            .apply(lambda x: str(x).upper() if pd.notna(x) else '')  # 直接转大写
            .tolist()
        )

        # 解析靶序列（取第一个非空值） - 只转大写
        target_sequence = None
        if len(df[target_col].dropna()) > 0:
            target_sequence = str(df[target_col].dropna().iloc[0]).upper()
        
        # 🔍 [DEBUG] 打印序列解析信息
        import sys
        print(f"[DEBUG sirna] 解析Excel文件: {excel_path}", file=sys.stderr)
        print(f"[DEBUG sirna] 查询序列数量: {len(query_sequences)}", file=sys.stderr)
        print(f"[DEBUG sirna] 查询序列前5个: {query_sequences[:5]}", file=sys.stderr)
        if target_sequence:
            print(f"[DEBUG sirna] 靶序列长度: {len(target_sequence)}", file=sys.stderr)
            print(f"[DEBUG sirna] 靶序列内容: {target_sequence[:50]}...", file=sys.stderr)

        # 预览模式直接返回
        if preview_mode:
            return query_sequences, target_sequence
            
        # 非预览模式下进行标准化
        query_sequences = [sanitize_seq(q) for q in query_sequences]
        target_sequence = sanitize_seq(target_sequence) if target_sequence else None
        
        return query_sequences, target_sequence
    except Exception as e:
        raise ValueError(f"Excel解析失败: {str(e)}")



def parse_sequences_from_fasta(fasta_files):
    """解析FASTA文件"""
    try:
        sequences = []
        names = []

        for fasta_file in fasta_files:
            for record in parse(fasta_file, "fasta"):
                # 🔍 [DEBUG] FASTA解析：将U替换为T便于比对
                seq_str = str(record.seq).upper().replace('U', 'T')
                sequences.append(seq_str)
                names.append(record.id)
                # 🔍 [DEBUG] FASTA序列: {seq_str[:30]}... (ID: {record.id})", file=sys.stderr)

        return sequences, names
    except Exception as e:
        raise ValueError(f"FASTA解析失败: {str(e)}")



def perform_sirna_analysis(excel_path, fasta_paths, output_filename="siRNA_匹配结果", max_mismatch=1):
    """
    执行完整的siRNA分析流程（仅序列匹配部分，BLAST搜索将由异步任务处理）

    参数:
        excel_path: Excel文件路径
        fasta_paths: FASTA文件路径列表
        output_filename: 输出文件名前缀（会自动净化特殊字符）

    返回:
        results: 分析结果列表
        output_path: 生成的Excel文件路径
        target_seq: 靶序列（用于后续BLAST搜索）
    """
    # 🔍 [DEBUG] 打印分析开始信息
    import sys
    print(f"[DEBUG sirna] 开始分析", file=sys.stderr)
    print(f"[DEBUG sirna] Excel路径: {excel_path}", file=sys.stderr)
    print(f"[DEBUG sirna] FASTA文件数量: {len(fasta_paths)}", file=sys.stderr)
    print(f"[DEBUG sirna] 最大错配数: {max_mismatch}", file=sys.stderr)
    # 净化输出文件名，移除中文字符和特殊字符，防止服务器错误
    safe_output_filename = sanitize_string_content(output_filename)
    if not safe_output_filename or safe_output_filename.isspace():
        safe_output_filename = "siRNA_匹配结果"
    # 限制长度为50字符
    safe_output_filename = safe_output_filename[:50].strip()
    # 替换为安全的文件名
    safe_output_filename = re.sub(r'[^\w\-.]', '_', safe_output_filename)
    if not safe_output_filename:
        safe_output_filename = "sirna_results"
    # 1. 解析输入数据
    query_seqs, target_seq = parse_sequences_from_excel(excel_path)
    if not target_seq:
        raise ValueError("Excel中未找到有效靶序列")

    # 🔍 [DEBUG] 打印序列解析后信息
    import sys
    print(f"[DEBUG sirna] 解析完成，查询序列数: {len(query_seqs)}", file=sys.stderr)
    print(f"[DEBUG sirna] 靶序列长度: {len(target_seq)}", file=sys.stderr)
    print(f"[DEBUG sirna] 靶序列前50碱基: {target_seq[:50]}...", file=sys.stderr)

    # 2. 准备结果数据结构
    excel_results = []
    literature_reports = OrderedDict()

    # 分析查询序列（保持原始输入顺序）
    for i, query in enumerate(query_seqs):
        strand, pos = check_sirna_match(query, target_seq, max_mismatch)
        # 提取匹配长度，处理可能的突出端标记
        match_length = 0
        if pos != "N/A":
            # 提取括号内的长度信息，处理可能的[存在突出端]标记
            if '(' in pos and 'bp)' in pos:
                # 找到括号位置
                left_paren = pos.index('(')
                right_paren = pos.index('bp)') + 2  # +2 是因为 'bp)' 长度为2
                # 提取括号内的部分并转换为整数
                length_str = pos[left_paren + 1:right_paren].replace('bp', '')
                match_length = int(length_str) if length_str.isdigit() else 0
        
        result = {
            '查询序列ID': f"Query_{i+1}",  # 严格按输入顺序编号
            '原始序号': i+1,             # 保留原始序号
            '序列内容': query,
            '链类型': strand,
            '匹配位置': pos,
            '匹配长度': match_length
        }
        excel_results.append(result)

        # 🔍 [DEBUG] 打印每条序列的匹配结果
        import sys
        if i < 3:  # 只打印前3条，避免日志过多
            print(f"[DEBUG sirna] 序列{i+1}: 长度={len(query)}, 链类型={strand}, 位置={pos}", file=sys.stderr)

    # 4. 分析每个FASTA文件
    for file_idx, fasta_path in enumerate(fasta_paths):
        file_name = os.path.splitext(os.path.basename(fasta_path))[0]
        try:
            # 解析FASTA文件
            fasta_seqs, fasta_names = parse_sequences_from_fasta([fasta_path])
            file_results = []
            
            # 分析每条序列
            for seq, name in zip(fasta_seqs, fasta_names):
                strand, pos = check_sirna_match(seq, target_seq, max_mismatch)
                if strand == "正义链" or strand == "反义链":  # 同时处理正义链和反义链
                    # 提取匹配长度，处理可能的突出端标记
                    match_length = 0
                    if pos != "N/A":
                        # 提取括号内的长度信息，处理可能的[存在突出端]标记
                        if '(' in pos and 'bp)' in pos:
                            # 找到括号位置
                            left_paren = pos.index('(')
                            right_paren = pos.index('bp)') + 2  # +2 是因为 'bp)' 长度为2
                            # 提取括号内的部分并转换为整数
                            length_str = pos[left_paren + 1:right_paren].replace('bp', '')
                            match_length = int(length_str) if length_str.isdigit() else 0

                    file_results.append({
                        '文献序列ID': name,
                        '序列内容': seq,
                        '链类型': strand,  # 添加链类型信息
                        '匹配位置': pos,
                        '匹配长度': match_length
                    })
            
            # 保存文献结果
            literature_reports[file_name] = file_results
            
            # 关联到主结果
            for excel_row in excel_results:
                # 同时处理正义链和反义链的匹配
                if excel_row['链类型'] == "正义链" or excel_row['链类型'] == "反义链":
                    # 传递查询序列的链类型，优先匹配相同链类型的文献序列
                    best_match = find_best_match(
                        excel_row['匹配位置'],
                        file_results,
                        excel_row['链类型']  # 传递链类型信息
                    )
                    if best_match:
                        excel_row[f'{file_name}_匹配ID'] = best_match['文献序列ID']
                        excel_row[f'{file_name}_位置'] = best_match['匹配位置']
        except Exception as e:
            literature_reports[file_name] = f"分析失败: {str(e)}"

    # 5. 生成Excel结果文件
    output_folder = os.path.join('static', 'sirna_outputs')
    os.makedirs(output_folder, exist_ok=True)

    # 按原始输入顺序排序
    df_results = pd.DataFrame(excel_results)
    df_results.sort_values(by=['原始序号'], inplace=True)

    # 重新排列列顺序，确保显示重要列
    columns = df_results.columns.tolist()
    # 确保关键列在前面
    key_columns = ['查询序列ID', '原始序号', '序列内容', '链类型', '匹配位置', '匹配长度']
    # 其他列按字母顺序排列
    other_columns = [col for col in columns if col not in key_columns]
    df_results = df_results[key_columns + other_columns]

    # 生成带时间戳的文件名 - 使用净化后的文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(output_folder, f'{safe_output_filename}_主报告_{timestamp}.xlsx')
    df_results.to_excel(output_path, index=False)

    # 生成文献报告 - 净化文件名以防止特殊字符错误
    for file_name, results in literature_reports.items():
        if isinstance(results, list) and results:
            # 按匹配长度排序
            lit_df = pd.DataFrame(results)
            lit_df.sort_values(by=['匹配长度', '文献序列ID'],
                             ascending=[False, True],
                             inplace=True)

            # 净化文件名
            safe_file_name = sanitize_string_content(file_name)
            safe_file_name = re.sub(r'[^\w\-.]', '_', safe_file_name)[:30]
            if not safe_file_name:
                safe_file_name = "literature"

            lit_report_path = os.path.join(
                output_folder,
                f"文献_{safe_file_name}_报告_{timestamp}.xlsx"
            )
            lit_df.to_excel(lit_report_path, index=False)

    # 生成用于前端显示的结果格式
    front_end_results = []
    for result in excel_results:
        # 转换为前端需要的格式
        front_end_result = {
            'query_id': result['查询序列ID'],
            'original_id': result['原始序号'],
            'sequence': result['序列内容'],
            'strand_type': result['链类型'],
            'match_position': result['匹配位置'],
            'match_length': result['匹配长度'],
            'fasta_ids': [],
            'fasta_match_positions': [],
            'fasta_sequences': [],  # 添加文献序列内容
            'alignment_details': {}  # 添加比对详情
        }

        # 为查询序列生成比对详情
        if result['链类型'] in ['正义链', '反义链'] and result['匹配位置'] != 'N/A':
            alignment = generate_alignment_details(
                result['序列内容'],
                target_seq,
                result['链类型'],
                max_mismatch
            )
            if alignment:
                front_end_result['query_alignment'] = alignment

        # 提取FASTA匹配信息
        for col in result.keys():
            if '_匹配ID' in col:
                fasta_id = result.get(col, '无')
                file_name = col.replace('_匹配ID', '')
                position = result.get(f'{file_name}_位置', '无')
                if fasta_id != '无':
                    front_end_result['fasta_ids'].append(fasta_id)
                    front_end_result['fasta_match_positions'].append(position)

                    # 从文献报告中查找对应的序列
                    if file_name in literature_reports and isinstance(literature_reports[file_name], list):
                        for lit_result in literature_reports[file_name]:
                            if lit_result['文献序列ID'] == fasta_id:
                                front_end_result['fasta_sequences'].append(lit_result['序列内容'])

                                # 为文献序列生成比对详情
                                if lit_result.get('链类型') and lit_result['匹配位置'] != 'N/A':
                                    alignment = generate_alignment_details(
                                        lit_result['序列内容'],
                                        target_seq,
                                        lit_result['链类型'],
                                        max_mismatch
                                    )
                                    if alignment:
                                        front_end_result['alignment_details'][fasta_id] = alignment
                                break

        # 如果没有FASTA匹配，设置默认值
        if not front_end_result['fasta_ids']:
            front_end_result['fasta_ids'] = ['无']
            front_end_result['fasta_match_positions'] = ['无']
            front_end_result['fasta_sequences'] = ['无']

        front_end_results.append(front_end_result)

    return front_end_results, output_path, target_seq



def generate_results_table(results, max_rows=10):
    """
    生成结果表格的HTML（包含序列比对可视化）

    参数:
        results: 分析结果列表
        max_rows: 最多显示的行数

    返回:
        table_html: HTML表格字符串
    """
    # 过滤只显示有FASTA匹配的结果（排除'无'的情况）
    filtered_results = [r for r in results if r.get('fasta_ids') and r['fasta_ids'][0] != '无']

    table_html = '<table class="results-table">'
    table_html += '<thead><tr>'
    table_html += '<th>查询序列ID</th>'
    table_html += '<th>链类型</th>'
    table_html += '<th>匹配位置</th>'
    table_html += '<th>匹配长度</th>'
    table_html += '<th>文献序列名称</th>'
    table_html += '<th>文献位置</th>'
    table_html += '<th>操作</th>'
    table_html += '</tr></thead><tbody>'

    for idx, result in enumerate(filtered_results[:max_rows]):
        result_id = f"result_{idx}"
        table_html += f'<tr id="{result_id}_row">'
        table_html += f'<td>{result["query_id"]}</td>'
        table_html += f'<td>{result["strand_type"]}</td>'
        table_html += f'<td>{result["match_position"]}</td>'
        table_html += f'<td>{result["match_length"]}</td>'

        # 显示FASTA匹配信息（逗号分隔）
        fasta_ids = ', '.join(result['fasta_ids'])
        fasta_positions = ', '.join(result['fasta_match_positions'])

        table_html += f'<td>{fasta_ids}</td>'
        table_html += f'<td>{fasta_positions}</td>'
        table_html += f'<td><button id="btn_{result_id}" class="btn btn-secondary" onclick="toggleAlignmentDetails(\'{result_id}\')" style="padding: 5px 10px; font-size: 12px;">查看比对</button></td>'
        table_html += '</tr>'

        # 添加比对详情行（默认隐藏）
        table_html += f'<tr id="{result_id}_details" style="display: none;">'
        table_html += f'<td colspan="7" style="padding: 20px; background-color: #f8f9fa;">'

        # 查询序列比对
        if result.get('query_alignment'):
            aln = result['query_alignment']
            table_html += generate_alignment_html('查询序列', aln, result['strand_type'])

        # 文献序列比对
        if result.get('alignment_details'):
            for fasta_id, fasta_seq in zip(result['fasta_ids'], result['fasta_sequences']):
                if fasta_id in result['alignment_details']:
                    lit_aln = result['alignment_details'][fasta_id]
                    # 获取文献序列的链类型
                    lit_strand = '正义链'  # 默认值
                    table_html += '<hr style="margin: 15px 0; border: none; border-top: 1px solid #ddd;">'
                    table_html += generate_alignment_html(f'文献序列: {fasta_id}', lit_aln, lit_strand)

        table_html += '</td></tr>'

    if len(filtered_results) > max_rows:
        table_html += '<tr><td colspan="7" style="text-align:center;">' \
                   + '...</td></tr>'
        table_html += '<tr><td colspan="7" style="text-align:center;">' \
                   + f'共 {len(filtered_results)} 条匹配结果，完整结果请下载Excel文件' \
                   + '</td></tr>'
    elif not filtered_results:
        table_html += '<tr><td colspan="7" style="text-align:center;">' \
                   + '未找到与FASTA序列匹配的结果</td></tr>'

    table_html += '</tbody></table>'

    return table_html


def generate_alignment_html(title, alignment, strand_type):
    """生成单个序列比对的HTML"""
    # 为每个比对元素生成唯一ID
    title_id = title.replace(':', '_').replace(',', '_')

    # 获取序列并确保长度一致（取最短长度）
    query_seq = alignment['query_aligned']
    target_seq = alignment['target_aligned']
    align_symbols = alignment['alignment_symbols']

    # 确保三个序列长度一致
    min_len = min(len(query_seq), len(target_seq), len(align_symbols))
    query_seq = query_seq[:min_len]
    target_seq = target_seq[:min_len]
    align_symbols = align_symbols[:min_len]

    # 生成查询序列HTML（带错配高亮）
    query_html = []
    for base, symbol in zip(query_seq, align_symbols):
        if symbol == '×':
            query_html.append(f'<span style="background-color: #ffcccc; color: #cc0000; font-weight: bold;">{base}</span>')
        else:
            query_html.append(f'<span style="color: #28a745;">{base}</span>')
    query_aligned_str = ''.join(query_html)

    # 生成比对符号HTML（带颜色）
    align_html = []
    for symbol in align_symbols:
        if symbol == '|':
            align_html.append('<span style="color: #28a745;">|</span>')
        else:
            align_html.append('<span style="color: #dc3545; font-weight: bold;">×</span>')
    alignment_symbols_str = ''.join(align_html)

    # 生成靶序列HTML（带错配高亮）
    target_html = []
    for base, symbol in zip(target_seq, align_symbols):
        if symbol == '×':
            target_html.append(f'<span style="background-color: #ffcccc; color: #cc0000; font-weight: bold;">{base}</span>')
        else:
            target_html.append(f'<span style="color: #28a745;">{base}</span>')
    target_aligned_str = ''.join(target_html)

    # 确定匹配度颜色
    match_color = '#28a745' if alignment['match_percent'] >= 90 else '#ffc107' if alignment['match_percent'] >= 80 else '#dc3545'
    
    html = f'''
    <div style="font-family: 'Courier New', monospace; font-size: 13px; line-height: 1.6;">
        <h4 style="margin: 0 0 10px 0; color: #333;">{title}</h4>
        <div style="background: white; padding: 15px; border-radius: 6px; border: 1px solid #e0e0e0;">
            <div style="margin-bottom: 8px;">
                <span style="color: #666;">链类型:</span>
                <strong>{strand_type}</strong>
                <span style="margin-left: 20px; color: #666;">位置:</span>
                <strong>{alignment['target_start']}-{alignment['target_end']}</strong>
                <span style="margin-left: 20px; color: #666;">长度:</span>
                <strong>{alignment['alignment_length']}bp</strong>
                <span style="margin-left: 20px; color: #666;">匹配度:</span>
                <strong style="color: {match_color};">{alignment['match_percent']}%</strong>
            </div>
            <div style="display: flex; flex-direction: column; gap: 5px;">
                <div style="word-break: break-all; color: #333;">
                    <span style="color: #999; margin-right: 10px;">查询:</span>
                    <span id="query_{title_id}">{query_aligned_str}</span>
                </div>
                <div style="word-break: break-all; color: #666;">
                    <span style="color: #999; margin-right: 10px;">&nbsp;&nbsp;&nbsp;&nbsp;</span>
                    <span id="alignment_{title_id}">{alignment_symbols_str}</span>
                </div>
                <div style="word-break: break-all; color: #333;">
                    <span style="color: #999; margin-right: 10px;">靶序列:</span>
                    <span id="target_{title_id}">{target_aligned_str}</span>
                </div>
            </div>
            {f'<div style="margin-top: 10px; padding: 8px; background: #fff3cd; border-radius: 4px; font-size: 12px;"><strong>错配位置:</strong> {", ".join(map(str, alignment["mismatch_positions"]))}</div>' if alignment["mismatch_positions"] else ''}
        </div>
    </div>
    '''
    return html
def colorize_alignment(alignment_symbols):
    """给比对符号着色"""
    result = []
    for symbol in alignment_symbols:
        if symbol == '|':
            result.append('<span style="color: #28a745;">|</span>')
        else:
            result.append('<span style="color: #dc3545; font-weight: bold;">×</span>')
    return ''.join(result)

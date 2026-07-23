"""专利序列检索路由 — 基于 BLAST+ -remote 的 NCBI 专利库检索"""
from flask import Blueprint, render_template, request, session, jsonify, send_file
import csv
import io
import json
import os
import re
import subprocess
import shutil
import tempfile
import textwrap
from pathlib import Path

from ncbi_patent_blast import (
    FIELDS, extract_patents, run_blast, write_query, parse_hits
)

patent_bp = Blueprint('patent', __name__, url_prefix='/patent')

# 程序 → 专利库映射
PROGRAM_DB = {
    'blastp': 'pataa',
    'blastn': 'patnt',
}


@patent_bp.route('/')
def index():
    return render_template('patent.html')


@patent_bp.route('/search', methods=['POST'])
def search():
    """
    提交序列到 NCBI 专利库 BLAST，返回 outfmt 6 格式结果 + 专利号。
    """
    try:
        sequence = re.sub(r'\s+', '', request.form.get('sequence', '')).upper()
        if not sequence:
            return jsonify({'status': 'error', 'message': '请输入序列'})

        program = request.form.get('program', 'auto')
        hitlist_size = int(request.form.get('hitlist_size', 50))
        evalue = float(request.form.get('evalue', 10))
        min_identity = float(request.form.get('min_identity', 0))
        min_qcov = float(request.form.get('min_qcov', 0))

        # 自动检测程序
        if program == 'auto':
            valid_dna = set('ACGTN')
            valid_rna = set('ACGUN')
            chars = set(sequence)
            if 'U' in sequence:
                program = 'blastn'
            elif chars.issubset(valid_dna):
                program = 'blastn'
            else:
                program = 'blastp'

        database = PROGRAM_DB.get(program, 'pataa')

        # 检查 BLAST+ 可用
        exe = shutil.which(program)
        if not exe:
            return jsonify({'status': 'error', 'message': f'未找到 {program}，请安装 NCBI BLAST+'})

        # 创建临时目录
        tmpdir = Path(tempfile.mkdtemp(prefix='patent_blast_'))
        try:
            # 写 fasta
            fasta_path = tmpdir / 'query.fasta'
            fasta_path.write_text(
                ">query\n" + "\n".join(textwrap.wrap(sequence, 80)) + "\n",
                encoding='utf-8'
            )

            # 运行 BLAST
            outfmt_spec = ' '.join(FIELDS)
            raw_tsv = tmpdir / 'raw_hits.tsv'
            cmd = [
                exe, '-remote',
                '-db', database,
                '-query', str(fasta_path),
                '-evalue', str(evalue),
                '-max_target_seqs', str(hitlist_size),
                '-outfmt', f'6 {outfmt_spec}',
                '-out', str(raw_tsv),
            ]

            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=600
            )
            if proc.returncode != 0:
                err = proc.stderr.strip() or proc.stdout.strip() or 'BLAST failed'
                return jsonify({'status': 'error', 'message': err[:300]})

            # 解析结果
            all_rows, best_hits = parse_hits(raw_tsv, min_identity, min_qcov)

            # 构建专利号去重列表（按 bitscore 排序）
            patent_entries = []
            seen_patents = set()
            for patent, row in sorted(best_hits.items(),
                                      key=lambda x: -float(x[1].get('bitscore') or 0)):
                patent_entries.append({
                    'patent': patent,
                    'accession': row.get('saccver', ''),
                    'identity': float(row.get('pident', 0)),
                    'qcov': float(row.get('qcovs', 0)),
                    'bitscore': float(row.get('bitscore', 0)),
                    'evalue': float(row.get('evalue', 0)),
                    'title': (row.get('stitle') or '')[:120],
                    'sseqid': row.get('sseqid', ''),
                })
                seen_patents.add(patent)

            # 专利号列表（去重排序）
            patent_numbers = sorted(set(p['patent'] for p in patent_entries))

            # 命中列表（all rows）
            hit_rows = []
            for row in all_rows:
                hit_rows.append({
                    'sseqid': row.get('sseqid', ''),
                    'saccver': row.get('saccver', ''),
                    'stitle': (row.get('stitle') or '')[:120],
                    'pident': float(row.get('pident', 0)),
                    'length': int(row.get('length', 0)),
                    'mismatch': int(row.get('mismatch', 0)),
                    'gapopen': int(row.get('gapopen', 0)),
                    'qstart': int(row.get('qstart', 0)),
                    'qend': int(row.get('qend', 0)),
                    'sstart': int(row.get('sstart', 0)),
                    'send': int(row.get('send', 0)),
                    'evalue': float(row.get('evalue', 0)),
                    'bitscore': float(row.get('bitscore', 0)),
                    'qcovs': float(row.get('qcovs', 0)),
                    'patents': row.get('patents', []),
                })

            # 存储 session 供下载
            session['patent_search_result'] = {
                'query': sequence[:200],
                'patent_numbers': patent_numbers,
                'patent_entries': patent_entries,
                'total_hits': len(all_rows),
                'unique_patents': len(patent_numbers),
                'program': program,
                'database': database,
            }

            return jsonify({
                'status': 'success',
                'message': f'检索完成，发现 {len(all_rows)} 条命中，'
                           f'提取到 {len(patent_numbers)} 个专利号',
                'statistics': {
                    'total_hits': len(all_rows),
                    'unique_patents': len(patent_numbers),
                    'query_length': len(sequence),
                    'program': program,
                    'database': database,
                },
                'patent_entries': patent_entries,
                'patent_numbers': patent_numbers,
                'hits': hit_rows[:100],  # 限制前端显示 100 条
            })

        finally:
            # 清理临时文件
            shutil.rmtree(tmpdir, ignore_errors=True)

    except subprocess.TimeoutExpired:
        return jsonify({'status': 'error', 'message': 'BLAST 超时（>600s），请重试或使用更短序列'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'检索失败: {str(e)}'})


@patent_bp.route('/download')
def download():
    """下载专利号列表 Excel（含详细命中信息）"""
    try:
        import pandas as pd

        result = session.get('patent_search_result')
        if not result:
            return render_template('error.html', message='未找到检索结果'), 400

        data = []
        for entry in result.get('patent_entries', []):
            data.append({
                '专利公开号': entry.get('patent', ''),
                'Accession': entry.get('accession', ''),
                '同一性(%)': entry.get('identity', 0),
                '查询覆盖度(%)': entry.get('qcov', 0),
                'Bitscore': entry.get('bitscore', 0),
                'E-value': entry.get('evalue', 0),
                '描述': entry.get('title', ''),
            })

        buffer = io.BytesIO()
        df = pd.DataFrame(data) if data else pd.DataFrame({
            '专利公开号': [], 'Accession': [], '同一性(%)': [],
            '查询覆盖度(%)': [], 'Bitscore': [], 'E-value': [], '描述': [],
        })
        with pd.ExcelWriter(buffer, engine='openpyxl') as w:
            df.to_excel(w, index=False, sheet_name='专利最佳命中')
        buffer.seek(0)

        return send_file(
            buffer, as_attachment=True,
            download_name='专利公开号列表.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        return render_template('error.html', message=f'下载失败: {str(e)}'), 500

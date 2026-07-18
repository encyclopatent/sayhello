"""序列比对与突变分析路由 - 基于编号序列的三序列比对"""
from flask import Blueprint, render_template, request, session, jsonify, send_file
from werkzeug.utils import secure_filename
import os
import io
import pandas as pd

compare_bp = Blueprint('compare', __name__, url_prefix='/compare')


@compare_bp.route('/')
def index():
    """Mutation analysis tool main page."""
    return render_template('compare.html')


@compare_bp.route('/analyze', methods=['POST'])
def analyze():
    """Handle single three-sequence comparison."""
    try:
        from compare_utils import compare_sequences

        ref_seq = re.sub(r'\s+', '', request.form.get('ref_sequence', '')).upper()
        num_seq = re.sub(r'\s+', '', request.form.get('num_sequence', '')).upper()
        tgt_seq = re.sub(r'\s+', '', request.form.get('tgt_sequence', '')).upper()

        if not ref_seq or not num_seq or not tgt_seq:
            return jsonify({'status': 'error', 'message': '请填写三个序列'})

        gapopen = float(request.form.get('param_gapopen', 10.0))
        gapextend = float(request.form.get('param_gapextend', 0.5))

        result = compare_sequences(ref_seq, num_seq, tgt_seq, gapopen, gapextend)

        # 只存储下载所需的最小数据到session（raw_results等大数据只返回给前端不存session）
        session['compare_result_mini'] = {
            'identity': result['identity'],
            'matches': result['matches'],
            'mismatches': result['mismatches'],
            'total_positions': result['total_positions'],
            'mutations': result['mutations'],
            'alignments_identity': {
                'ref_vs_num': result['alignments']['ref_vs_num']['identity'],
                'tgt_vs_num': result['alignments']['tgt_vs_num']['identity'],
            },
        }

        return jsonify({'status': 'success', 'result': result})

    except Exception as e:
        return jsonify({'status': 'error', 'message': f'比对失败：{str(e)}'})


@compare_bp.route('/batch', methods=['POST'])
def batch():
    """Handle batch Excel upload comparison."""
    try:
        from compare_utils import batch_compare_from_excel

        if 'excel_file' not in request.files:
            return jsonify({'status': 'error', 'message': '未选择Excel文件'})

        excel_file = request.files['excel_file']
        if excel_file.filename == '':
            return jsonify({'status': 'error', 'message': '未选择Excel文件'})

        upload_folder = os.path.join('static', 'compare_uploads')
        os.makedirs(upload_folder, exist_ok=True)

        filename = secure_filename(excel_file.filename)
        excel_path = os.path.join(upload_folder, filename)
        excel_file.save(excel_path)

        gapopen = float(request.form.get('param_gapopen', 10.0))
        gapextend = float(request.form.get('param_gapextend', 0.5))

        results = batch_compare_from_excel(excel_path, gapopen, gapextend)

        # 清理上传文件
        if os.path.exists(excel_path):
            os.remove(excel_path)

        # 只存储下载所需的最小数据到session（剔除alignments/raw_results等大数据）
        session['compare_batch_results'] = [
            {
                'name': r.get('name', ''),
                'index': r.get('index', 0),
                'identity': r['identity'],
                'matches': r['matches'],
                'mismatches': r['mismatches'],
                'total_positions': r['total_positions'],
                'mutations': r['mutations'],
            }
            for r in results
        ]

        return jsonify({'status': 'success', 'results': results, 'count': len(results)})

    except Exception as e:
        return jsonify({'status': 'error', 'message': f'批量处理失败：{str(e)}'})


@compare_bp.route('/download/excel')
def download_excel():
    """Download single comparison result as Excel."""
    try:
        result = session.get('compare_result_mini')
        if not result:
            return render_template('error.html', message='未找到比对结果'), 400

        data = []

        # 同一性汇总行
        data.append({
            '分析项目': '序列同一性',
            '参比-编号同一性': f"{result['alignments_identity']['ref_vs_num']:.2%}",
            '目标-编号同一性': f"{result['alignments_identity']['tgt_vs_num']:.2%}",
            '参比-目标同一性': f"{result['identity']:.2%}",
            '匹配/总比对': f"{result['matches']}/{result['total_positions']}",
            '突变数': len(result['mutations']),
        })

        # 突变明细
        for m in result['mutations']:
            data.append({
                '分析项目': '突变位点',
                '编号位置': m['numbering_position'],
                '参比序列残基': m['reference_residue'],
                '目标序列残基': m['target_residue'],
                '突变表示': f"{m['reference_residue']}{m['numbering_position']}{m['target_residue']}",
            })

        buffer = io.BytesIO()
        df = pd.DataFrame(data)
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='序列比对突变分析')
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name='序列比对突变分析.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except Exception as e:
        return render_template('error.html', message=f'下载失败：{str(e)}'), 500


@compare_bp.route('/download/batch')
def download_batch():
    """Download batch comparison summary as Excel."""
    try:
        results = session.get('compare_batch_results')
        if not results:
            return render_template('error.html', message='未找到批量比对结果'), 400

        rows = []
        for r in results:
            rows.append({
                '序列名称': r.get('name', ''),
                '序列同一性': f"{r['identity']:.2%}",
                '匹配数': r['matches'],
                '错配数': r['mismatches'],
                '总比对位置': r['total_positions'],
                '突变数量': len(r['mutations']),
            })

        buffer = io.BytesIO()
        df = pd.DataFrame(rows)
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='批量比对汇总')
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name='批量比对汇总.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except Exception as e:
        return render_template('error.html', message=f'下载失败：{str(e)}'), 500


# 导入re模块（用于analyze中）
import re

"""三序列比对与突变分析路由 - 基于编号序列坐标系统的比对"""
from flask import Blueprint, render_template, request, session, jsonify, send_file
from werkzeug.utils import secure_filename
import os
import io
import re

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

        # 只存储下载所需的最小数据到session
        session['compare_result_mini'] = {
            'longest_identity': result['longest_identity'],
            'core_identity': result['core_identity'],
            'core_matches': result['core_matches'],
            'core_length': result['core_length'],
            'total_mutations': result['total_mutations'],
            'mutation_string': result.get('mutation_string', ''),
            'mutations': result['mutations'],
            'alignments_identity': {
                'ref_vs_num': round(result['alignments']['ref_vs_num'].get('longest_identity', result['alignments']['ref_vs_num']['identity']) * 100, 2),
                'ref_vs_tgt_core': result['core_identity'],
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

        stem = secure_filename(excel_file.filename)
        if not stem:
            stem = 'upload'
        filename = stem + '.xlsx'
        excel_path = os.path.join(upload_folder, filename)
        excel_file.save(excel_path)

        gapopen = float(request.form.get('param_gapopen', 10.0))
        gapextend = float(request.form.get('param_gapextend', 0.5))

        results = batch_compare_from_excel(excel_path, gapopen, gapextend)

        # 保存文件路径供下载使用
        session['compare_batch_file'] = excel_path

        # 只存储下载所需的最小数据到session
        session['compare_batch_results'] = [
            {
                'name': r.get('name', ''),
                'index': r.get('index', 0),
                'core_identity': r['core_identity'],
                'longest_identity': r['longest_identity'],
                'core_matches': r['core_matches'],
                'core_length': r['core_length'],
                'total_mutations': r['total_mutations'],
                'mutation_string': r.get('mutation_string', ''),
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

        import pandas as pd

        data = []

        # 同一性汇总行
        data.append({
            '分析项目': '核心区间同一性',
            '值': f"{result['core_identity']}%",
        })
        data.append({
            '分析项目': 'needle最长一致性',
            '值': f"{result['longest_identity']}%",
        })
        data.append({
            '分析项目': '核心区间匹配/总长',
            '值': f"{result['core_matches']}/{result['core_length']}",
        })
        data.append({
            '分析项目': '突变总数',
            '值': result['total_mutations'],
        })
        data.append({
            '分析项目': '突变位点字符串',
            '值': result.get('mutation_string', ''),
        })

        # 突变明细
        for m in result['mutations']:
            data.append({
                '分析项目': '突变位点',
                '值': m.get('mutation_string', f"{m['reference_residue']}{m['numbering_position']}{m['target_residue']}"),
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
    """在原上传Excel基础上追加序列同一性和突变位点列表后下载。"""
    try:
        import pandas as pd

        results = session.get('compare_batch_results')
        file_path = session.get('compare_batch_file')
        if not results or not file_path or not os.path.exists(file_path):
            return render_template('error.html', message='未找到批量比对结果'), 400

        # 读取原始上传的Excel
        df = pd.read_excel(file_path, engine='openpyxl')

        # 读完后清理上传文件
        try:
            os.remove(file_path)
        except OSError:
            pass
        session.pop('compare_batch_file', None)

        # 追加序列同一性列（核心区间同一性）
        identities = [f"{r.get('core_identity', r.get('longest_identity', 0))}%" for r in results]
        df['序列同一性'] = identities

        # 追加突变位点列表列（"/"连接，如 S3T/N43R）
        df['突变位点列表'] = [r.get('mutation_string', '') or '-' for r in results]

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='批量比对结果')
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name='批量比对结果.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except Exception as e:
        return render_template('error.html', message=f'下载失败：{str(e)}'), 500

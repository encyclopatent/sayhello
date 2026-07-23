"""序列理化性质分析路由"""
from flask import Blueprint, render_template, request, session, jsonify, send_file
from werkzeug.utils import secure_filename
import os
import io
import pandas as pd

prop_bp = Blueprint('property', __name__, url_prefix='/property')


@prop_bp.route('/')
def index():
    return render_template('seq_property.html')


@prop_bp.route('/analyze', methods=['POST'])
def analyze():
    try:
        from seq_property import analyze_sequence

        seq = request.form.get('sequence', '').strip()
        name = request.form.get('seq_name', '').strip() or '序列1'

        if not seq:
            return jsonify({'status': 'error', 'message': '请输入序列'})

        result = analyze_sequence(seq, name)
        return jsonify({'status': 'success', 'result': result})

    except Exception as e:
        return jsonify({'status': 'error', 'message': f'分析失败：{str(e)}'})


@prop_bp.route('/batch', methods=['POST'])
def batch():
    try:
        from seq_property import batch_analyze_excel

        if 'excel_file' not in request.files:
            return jsonify({'status': 'error', 'message': '未选择文件'})

        excel_file = request.files['excel_file']
        if excel_file.filename == '':
            return jsonify({'status': 'error', 'message': '未选择文件'})

        upload_folder = os.path.join('static', 'prop_uploads')
        os.makedirs(upload_folder, exist_ok=True)
        filename = secure_filename(excel_file.filename)
        excel_path = os.path.join(upload_folder, filename)
        excel_file.save(excel_path)

        results = batch_analyze_excel(excel_path)

        if os.path.exists(excel_path):
            os.remove(excel_path)

        session['prop_batch'] = results
        return jsonify({'status': 'success', 'results': results, 'count': len(results)})

    except Exception as e:
        return jsonify({'status': 'error', 'message': f'批量分析失败：{str(e)}'})


@prop_bp.route('/download')
def download():
    try:
        results = session.get('prop_batch')
        if not results:
            return render_template('error.html', message='未找到分析结果'), 400

        rows = []
        for r in results:
            row = {'名称': r.get('name', ''), '分子类型': r.get('moltype', ''), '长度': r.get('clean_length', 0), '分子量': r.get('molecular_weight', 0)}

            if r.get('nucleic'):
                n = r['nucleic']
                row['GC含量(%)'] = n.get('gc_pct', 0)
                row['Tm基本(°C)'] = n.get('tm_basic', 0)
                row['Tm短链(°C)'] = n.get('tm_wallace', 0)
                row['A(%)'] = n.get('base_pct', {}).get('A', 0)
                row['T/U(%)'] = n.get('base_pct', {}).get('T', 0) or n.get('base_pct', {}).get('U', 0)
                row['G(%)'] = n.get('base_pct', {}).get('G', 0)
                row['C(%)'] = n.get('base_pct', {}).get('C', 0)

            if r.get('protein'):
                p = r['protein']
                row['等电点(pI)'] = p.get('pI', 0)
                row['GRAVY'] = p.get('gravy', 0)
                row['脂肪指数'] = p.get('aliphatic_index', 0)
                row['不稳定指数'] = p.get('instability_index', 0)
                row['稳定性分类'] = p.get('instability_class', '')
                row['消光系数(还原)'] = p.get('extinction_280_reduced', 0)
                row['消光系数(氧化)'] = p.get('extinction_280_oxidized', 0)
                row['pH7净电荷'] = p.get('charge_ph7', 0)

            rows.append(row)

        buffer = io.BytesIO()
        df = pd.DataFrame(rows)
        with pd.ExcelWriter(buffer, engine='openpyxl') as w:
            df.to_excel(w, index=False, sheet_name='序列性质')
        buffer.seek(0)

        return send_file(buffer, as_attachment=True, download_name='序列性质分析.xlsx',
                        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    except Exception as e:
        return render_template('error.html', message=f'下载失败：{str(e)}'), 500

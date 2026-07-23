"""专利序列检索路由 — NCBI BLAST 专利库"""
from flask import Blueprint, render_template, request, session, jsonify, send_file
from werkzeug.utils import secure_filename
import os
import io
import re

patent_bp = Blueprint('patent', __name__, url_prefix='/patent')


@patent_bp.route('/')
def index():
    return render_template('patent.html')


@patent_bp.route('/search', methods=['POST'])
def search():
    try:
        from patent_search import search_patents

        sequence = re.sub(r'\s+', '', request.form.get('sequence', '')).upper()
        if not sequence:
            return jsonify({'status': 'error', 'message': '请输入序列'})

        program = request.form.get('program', 'auto')
        hitlist_size = int(request.form.get('hitlist_size', 50))

        result = search_patents(sequence, program=program, hitlist_size=hitlist_size)

        # 存session供下载用
        if result['status'] == 'success':
            session['patent_search_result'] = {
                'query': sequence[:200],
                'patent_numbers': result['patent_numbers'],
                'total_hits': result['statistics'].get('total_hits', 0),
                'rid': result.get('rid', ''),
            }

        return jsonify(result)

    except Exception as e:
        return jsonify({'status': 'error', 'message': f'检索失败: {str(e)}'})


@patent_bp.route('/status', methods=['POST'])
def status_check():
    """查询之前提交的BLAST任务状态（手动轮询用）"""
    try:
        from patent_search import poll_blast, parse_blast_xml

        rid = request.form.get('rid', '').strip()
        if not rid:
            return jsonify({'status': 'error', 'message': '缺少RID'})

        xml_text, error = poll_blast(rid, max_wait=60, poll_interval=3)
        if error:
            return jsonify({'status': 'pending', 'message': error})

        parsed = parse_blast_xml(xml_text)
        parsed['status'] = 'success'
        return jsonify(parsed)

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


@patent_bp.route('/download')
def download():
    """下载专利号列表为Excel"""
    try:
        import pandas as pd

        result = session.get('patent_search_result')
        if not result:
            return render_template('error.html', message='未找到检索结果'), 400

        data = []
        for pn in result.get('patent_numbers', []):
            data.append({'专利公开号': pn})

        buffer = io.BytesIO()
        df = pd.DataFrame(data) if data else pd.DataFrame({'专利公开号': []})
        with pd.ExcelWriter(buffer, engine='openpyxl') as w:
            df.to_excel(w, index=False, sheet_name='专利公开号')
        buffer.seek(0)

        return send_file(
            buffer, as_attachment=True,
            download_name='专利公开号列表.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        return render_template('error.html', message=f'下载失败: {str(e)}'), 500

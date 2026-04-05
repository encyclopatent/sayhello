"""Sequence alignment routes."""
from flask import Blueprint, render_template, request, session, jsonify, send_file
import os
import re
import io
import pandas as pd

alignment_bp = Blueprint('alignment', __name__, url_prefix='/alignment')


@alignment_bp.route('/')
def index():
    """Alignment tool main page."""
    return render_template('alignment.html')


@alignment_bp.route('/analyze', methods=['POST'])
def analyze():
    """Handle sequence alignment request."""
    try:
        from alignment_utils import process_alignment

        target_sequence = re.sub(r'\s+', '', request.form.get('target_sequence', '').strip()).upper()
        query_sequence = re.sub(r'\s+', '', request.form.get('query_sequence', '').strip()).upper()
        target_sites_str = request.form.get('target_sites', '').strip()
        key_positions_str = request.form.get('key_positions', '').strip()
        algorithm = 'global'

        target_sites = []
        if target_sites_str:
            target_sites = [int(m.group()) for m in re.finditer(r'\d+', target_sites_str)]

        key_positions = set()
        if key_positions_str:
            key_positions = {int(m.group()) for m in re.finditer(r'\d+', key_positions_str)}

        alignment_results = process_alignment(target_sequence, query_sequence, target_sites, key_positions, algorithm)

        session['alignment_results'] = alignment_results
        session['target_sequence'] = target_sequence
        session['query_sequence'] = query_sequence
        session['target_sites'] = target_sites
        session['key_positions'] = list(key_positions)
        session['algorithm'] = algorithm

        return jsonify({
            'status': 'success',
            'results': alignment_results['results'],
            'algorithm': algorithm,
            'target_sequence': target_sequence,
            'query_sequence': query_sequence,
            'target_sites': target_sites,
            'key_positions': list(key_positions)
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'比对失败：{str(e)}'})


@alignment_bp.route('/download/excel')
def download_excel():
    """Download alignment results as Excel."""
    try:
        alignment_results = session.get('alignment_results')
        if not alignment_results:
            return render_template('error.html', message='未找到比对结果，请先完成序列比对'), 400

        results = alignment_results['results']
        buffer = io.BytesIO()
        df = pd.DataFrame(results)
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='比对结果')
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name='序列比对结果.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        return render_template('error.html', message=f'下载失败：{str(e)}'), 500


@alignment_bp.route('/download/needle')
def download_needle():
    """Download needle alignment raw result."""
    try:
        alignment_results = session.get('alignment_results')
        if not alignment_results:
            return render_template('error.html', message='未找到比对结果，请先完成序列比对'), 400

        needle_raw_result = alignment_results.get('needle_raw_result', '')
        if not needle_raw_result:
            return render_template('error.html', message='未找到needle比对结果'), 400

        buffer = io.BytesIO()
        buffer.write(needle_raw_result.encode('utf-8'))
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name='needle比对结果.txt',
            mimetype='text/plain'
        )
    except Exception as e:
        return render_template('error.html', message=f'下载失败：{str(e)}'), 500

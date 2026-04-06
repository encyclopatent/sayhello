"""siRNA analysis routes."""
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash, send_file
from werkzeug.utils import secure_filename
import os
import re
import io

sirna_bp = Blueprint('sirna', __name__, url_prefix='/sirna')


@sirna_bp.route('/')
def index():
    """siRNA tool main page."""
    return render_template('sirna.html')


@sirna_bp.route('/upload', methods=['POST'])
def upload():
    """Handle file upload for siRNA analysis."""
    import sirna_analysis

    try:
        sirna_upload_folder = os.path.join('static', 'sirna_uploads')
        os.makedirs(sirna_upload_folder, exist_ok=True)

        if 'excel_file' not in request.files:
            return jsonify({'status': 'error', 'message': '未选择Excel文件'})

        excel_file = request.files['excel_file']
        if excel_file.filename == '':
            return jsonify({'status': 'error', 'message': '未选择Excel文件'})

        original_filename = excel_file.filename
        base_name = secure_filename(original_filename)
        safe_filename = re.sub(r'[^\w\-.]', '_', base_name)[:100]
        if not safe_filename or safe_filename.startswith('.'):
            safe_filename = 'sirna_upload.xlsx'
        if not safe_filename.endswith('.xlsx') and not safe_filename.endswith('.xls'):
            safe_filename = safe_filename.rsplit('.', 1)[0] + '.xlsx'

        excel_path = os.path.join(sirna_upload_folder, safe_filename)
        excel_file.save(excel_path)

        # Handle FASTA files
        fasta_paths = []
        if 'fasta_files' in request.files:
            fasta_files = request.files.getlist('fasta_files')
            for fasta_file in fasta_files:
                if fasta_file.filename != '':
                    fasta_base = secure_filename(fasta_file.filename)
                    fasta_safe = re.sub(r'[^\w\-.]', '_', fasta_base)[:100]
                    if not fasta_safe or fasta_safe.startswith('.'):
                        fasta_safe = f'fasta_{len(fasta_paths)+1}.fasta'
                    if not fasta_safe.endswith('.fasta') and not fasta_safe.endswith('.fa'):
                        ext = os.path.splitext(fasta_base)[1]
                        if ext and ext in ['.fasta', '.fa']:
                            fasta_safe = fasta_safe.rsplit('.', 1)[0] + ext
                        else:
                            fasta_safe = fasta_safe.rsplit('.', 1)[0] + '.fasta'

                    fasta_path = os.path.join(sirna_upload_folder, fasta_safe)
                    fasta_file.save(fasta_path)
                    fasta_paths.append(fasta_path)

        session['sirna_excel_path'] = excel_path
        session['sirna_fasta_paths'] = fasta_paths
        session['sirna_output_filename'] = request.form.get('output_filename', 'siRNA_匹配结果')
        session['sirna_mismatch_count'] = int(request.form.get('mismatch_count', 1))

        # Parse files for preview
        query_seqs, target_sequence = sirna_analysis.parse_sequences_from_excel(excel_path, preview_mode=True)
        fasta_sequences, fasta_names = sirna_analysis.parse_sequences_from_fasta(fasta_paths)

        preview_text = f"Excel文件：{safe_filename}\n"
        preview_text += f"查询序列数量：{len(query_seqs)}\n"

        if target_sequence:
            preview_text += f"Excel靶序列长度：{len(target_sequence)}nt\n\n"
        else:
            preview_text += "Excel靶序列：无\n\n"

        preview_text += f"FASTA文件数量：{len(fasta_paths)}\n"
        for i, fasta_file in enumerate(fasta_paths):
            preview_text += f"FASTA {i+1}：{os.path.basename(fasta_file)}\n"
        preview_text += f"FASTA序列数量：{len(fasta_sequences)}\n"

        return jsonify({
            'status': 'success',
            'message': '文件上传成功',
            'preview_text': preview_text
        })

    except Exception as e:
        return jsonify({'status': 'error', 'message': f'文件上传失败：{str(e)}'})


@sirna_bp.route('/analyze', methods=['POST'])
def analyze():
    """Handle siRNA analysis request."""
    from tasks import blast_search_task
    import sirna_analysis

    try:
        excel_path = session.get('sirna_excel_path')
        fasta_paths = session.get('sirna_fasta_paths', [])
        output_filename = session.get('sirna_output_filename', 'siRNA_匹配结果')

        if not excel_path or not os.path.exists(excel_path):
            return jsonify({'status': 'error', 'message': 'Excel文件不存在'})

        mismatch_count = session.get('sirna_mismatch_count', 1)

        front_end_results, output_path, target_seq = sirna_analysis.perform_sirna_analysis(
            excel_path, fasta_paths, output_filename, mismatch_count
        )

        session['sirna_results_path'] = output_path

        table_html = sirna_analysis.generate_results_table(front_end_results, max_rows=10)

        filtered_results = [r for r in front_end_results if r.get('fasta_ids') and r['fasta_ids'][0] != '无']

        blast_task = blast_search_task.delay(target_seq)
        session['blast_task_id'] = blast_task.id

        blast_html = '<div class="blast-results">'
        blast_html += '<h3>靶序列验证结果</h3>'
        blast_html += '<p id="blast-status" style="color: orange;">正连接NCBI验证靶序列...</p>'
        blast_html += '<div id="blast-results-content"></div>'
        blast_html += '</div>'

        return jsonify({
            'status': 'success',
            'message': '分析完成',
            'results_table': table_html,
            'blast_results': blast_html,
            'total_results': len(filtered_results),
            'full_results_count': len(front_end_results),
            'blast_task_id': blast_task.id
        })

    except Exception as e:
        return jsonify({'status': 'error', 'message': f'分析失败：{str(e)}'})


@sirna_bp.route('/blast_status/<task_id>')
def blast_status(task_id):
    """Check BLAST search task status."""
    from tasks import blast_search_task

    try:
        task = blast_search_task.AsyncResult(task_id)

        if task.state == 'PENDING':
            response = {'state': task.state, 'status': '正连接NCBI验证靶序列...', 'blast_results': None}
        elif task.state == 'PROGRESS':
            response = {'state': task.state, 'status': '正连接NCBI验证靶序列...', 'blast_results': None}
        elif task.state == 'SUCCESS':
            blast_results = task.result

            blast_html = '<table class="blast-table">'
            blast_html += '<thead><tr>'
            blast_html += '<th>NCBI ID</th><th>描述</th><th>匹配长度</th><th>一致性(%)</th><th>E值</th>'
            blast_html += '</tr></thead><tbody>'

            for blast_result in blast_results[:2]:
                blast_html += '<tr>'
                blast_html += f'<td>{blast_result["ncbi_id"]}</td>'
                blast_html += f'<td>{blast_result["description"]}</td>'
                blast_html += f'<td>{blast_result["match_length"]}</td>'
                blast_html += f'<td>{blast_result["identity_percent"]:.2f}</td>'
                blast_html += f'<td>{blast_result["evalue"]:.2e}</td>'
                blast_html += '</tr>'

            blast_html += '</tbody></table>'
            if len(blast_results) > 2:
                blast_html += f'<p>共找到 {len(blast_results)} 个匹配结果，仅显示前2个。</p>'

            response = {'state': task.state, 'status': '验证完成', 'blast_results': blast_html}
        elif task.state == 'FAILURE':
            response = {'state': task.state, 'status': f'验证失败: {str(task.info)}', 'blast_results': None}
        else:
            response = {'state': task.state, 'status': f'任务状态: {task.state}', 'blast_results': None}

        return jsonify(response)
    except Exception as e:
        return jsonify({'state': 'ERROR', 'status': f'获取验证状态失败: {str(e)}', 'blast_results': None}), 500


@sirna_bp.route('/download')
def download():
    """Download siRNA analysis results."""
    try:
        results_path = session.get('sirna_results_path')
        excel_path = session.get('sirna_excel_path')
        fasta_paths = session.get('sirna_fasta_paths', [])

        if not results_path or not os.path.exists(results_path):
            return redirect(url_for('sirna.index'))

        filename = os.path.basename(results_path)

        buffer = io.BytesIO()
        with open(results_path, 'rb') as f:
            buffer.write(f.read())
        buffer.seek(0)

        files_to_delete = [results_path, excel_path] + fasta_paths
        for path in files_to_delete:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass

        session.pop('sirna_results_path', None)
        session.pop('sirna_excel_path', None)
        session.pop('sirna_fasta_paths', None)
        session.pop('sirna_output_filename', None)
        session.pop('blast_task_id', None)

        return send_file(
            buffer,
            as_attachment=True,
            attachment_filename=filename,
            mimetype='application/vnd.ms-excel'
        )

    except Exception as e:
        return redirect(url_for('sirna.index'))

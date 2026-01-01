from flask import (
    Flask, render_template, request, flash, redirect, url_for,
    send_file, session, jsonify, make_response
)
from types import SimpleNamespace
import json
import os
import uuid
import logging
from datetime import datetime
from werkzeug.utils import secure_filename
from st26autonew import convert_excel_to_xml
from celery import Celery
import pandas as pd
from Bio.Seq import Seq
from Bio.SeqIO import parse
import re

# 导入siRNA分析模块
import sirna_analysis


app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 需要设置secret_key以使用flash

# 配置日志记录
log_dir = 'logs'
os.makedirs(log_dir, exist_ok=True)

# 创建日志格式
log_format = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 配置文件日志
file_handler = logging.FileHandler(
    f'{log_dir}/app_{datetime.now().strftime("%Y%m%d")}.log'
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(log_format)

# 配置控制台日志
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(log_format)

# 将日志处理器添加到应用
app.logger.addHandler(file_handler)
app.logger.addHandler(console_handler)
app.logger.setLevel(logging.INFO)

# 确保上传文件夹和生成XML文件夹存在
UPLOAD_FOLDER = os.path.join('static', 'uploads')
OUTPUTS_FOLDER = os.path.join('static', 'outputs')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUTS_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUTS_FOLDER'] = OUTPUTS_FOLDER

# Celery配置
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'

# 创建Celery实例
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)


# siRNA工具核心功能已移至sirna_analysis.py模块


@app.route('/')
def main():
    """主页面路由"""
    return render_template('main.html')


@app.route('/st26')
def st26_index():
    """ST26工具主页面"""
    # 设置响应头，防止浏览器缓存页面
    response = make_response()
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    # 获取当前session中的数据用于渲染模板
    xml_file = session.get('xml_file', None)
    sequence_summary = session.get('sequence_summary', None)
    reminders = session.get('reminders', None)
    task_id = session.get('task_id', None)
    original_filename = session.get('original_filename', None)
    uploaded_file_path = session.get('uploaded_file_path', None)
    error_message = session.get('error_message', None)
    error_sequence = session.get('error_sequence', None)
    error_position = session.get('error_position', None)
    
    # 清除所有会话数据
    # 只有当用户正在进行一个未完成的任务时，才保留task_id相关的数据
    # 这样可以确保每次重新访问页面时都不会显示上一个用户的残留数据
    if task_id and not xml_file:
        # 用户正在进行一个未完成的任务，保留必要的任务数据
        session.clear()
        # 重新保存必要的任务数据
        session['task_id'] = task_id
        session['uploaded_file_path'] = uploaded_file_path
        session['original_filename'] = original_filename
    else:
        # 否则，清除所有会话数据
        session.clear()
    
    response.set_data(render_template(
        'index.html',
        xml_file=xml_file,
        sequence_summary=sequence_summary,
        reminders=reminders,
        task_id=task_id,
        original_filename=original_filename,
        error_message=error_message,
        error_sequence=error_sequence,
        error_position=error_position
    ))
    return response


@app.route('/sirna')
def sirna_index():
    """siRNA工具主页面"""
    return render_template('sirna.html')


@app.route('/fragment')
def fragment_index():
    """化合物拆解工具主页面"""
    return render_template('fragment.html')


@app.route('/fragment/process', methods=['POST'])
def fragment_process():
    """处理化合物拆解请求"""
    try:
        # 确保上传文件夹存在
        upload_folder = os.path.join('static', 'fragment_uploads')
        output_folder = os.path.join('static', 'fragment_outputs')
        os.makedirs(upload_folder, exist_ok=True)
        os.makedirs(output_folder, exist_ok=True)

        # 处理上传的Excel文件
        if 'excel_file' not in request.files:
            return jsonify({'status': 'error', 'message': '未选择Excel文件'})

        excel_file = request.files['excel_file']
        if excel_file.filename == '':
            return jsonify({'status': 'error', 'message': '未选择Excel文件'})

        # 保存Excel文件
        filename = secure_filename(excel_file.filename)
        excel_path = os.path.join(upload_folder, filename)
        excel_file.save(excel_path)

        # 导入并使用化合物拆解功能
        import sys
        sys.path.append('/Users/zhaoyongjiang/Downloads')
        from peptide2fragment import process_compounds as process_fragments

        # 处理化合物
        result_path, stats_path, images_dir, summary = process_fragments(excel_path, output_folder)

        return jsonify({
            'status': 'success',
            'message': '处理完成',
            'result_path': result_path,
            'stats_path': stats_path,
            'images_dir': images_dir,
            'summary': summary
        })
    except Exception as e:
        app.logger.error(f'Fragment processing error: {str(e)}')
        return jsonify({'status': 'error', 'message': f'处理失败：{str(e)}'})


@app.route('/fragment/download/<path:filename>')
def fragment_download(filename):
    """下载化合物拆解结果文件"""
    try:
        return send_file(
            os.path.join('static', 'fragment_outputs', filename),
            as_attachment=True
        )
    except Exception as e:
        app.logger.error(f'Download error: {str(e)}')
        return jsonify({'status': 'error', 'message': f'下载失败：{str(e)}'})


@app.route('/alignment')
def alignment_index():
    """序列比对工具主页面"""
    return render_template('alignment.html')


@app.route('/alignment/analyze', methods=['POST'])
def alignment_analyze():
    """处理序列比对请求"""
    try:
        # 导入序列比对工具函数
        from alignment_utils import process_alignment
        
        # 获取表单数据
        target_sequence = request.form.get('target_sequence', '').strip().upper().replace('\s+', '')
        query_sequence = request.form.get('query_sequence', '').strip().upper().replace('\s+', '')
        target_sites_str = request.form.get('target_sites', '').strip()
        key_positions_str = request.form.get('key_positions', '').strip()
        algorithm = 'global'  # 默认使用全局比对算法
        
        # 解析靶序列特定位点
        target_sites = []
        if target_sites_str:
            target_sites = [int(m.group()) for m in re.finditer(r'\d+', target_sites_str)]
        
        # 解析查询序列关键位点
        key_positions = set()
        if key_positions_str:
            key_positions = {int(m.group()) for m in re.finditer(r'\d+', key_positions_str)}
        
        # 执行序列比对
        alignment_results = process_alignment(target_sequence, query_sequence, target_sites, key_positions, algorithm)
        
        # 存储结果到session，用于后续下载
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
        app.logger.error(f'Alignment processing error: {str(e)}')
        import traceback
        app.logger.error(f'Alignment processing traceback: {traceback.format_exc()}')
        return jsonify({'status': 'error', 'message': f'比对失败：{str(e)}'})


@app.route('/alignment/download/excel')
def alignment_download_excel():
    """下载比对结果的Excel文件"""
    try:
        # 从session获取比对结果
        alignment_results = session.get('alignment_results')
        if not alignment_results:
            return render_template('error.html', message='未找到比对结果，请先完成序列比对'), 400
        
        results = alignment_results['results']
        
        # 使用pandas生成Excel文件
        import pandas as pd
        import io
        
        # 创建DataFrame
        df = pd.DataFrame(results)
        
        # 创建Excel文件在内存中
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='比对结果')
        buffer.seek(0)
        
        # 返回文件下载
        return send_file(
            buffer,
            as_attachment=True,
            download_name='序列比对结果.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        app.logger.error(f'Excel download error: {str(e)}')
        return render_template('error.html', message=f'下载失败：{str(e)}'), 500


@app.route('/alignment/download/needle')
def alignment_download_needle():
    """下载needle比对结果的原始txt文件"""
    try:
        # 从session获取比对结果
        alignment_results = session.get('alignment_results')
        if not alignment_results:
            return render_template('error.html', message='未找到比对结果，请先完成序列比对'), 400
        
        needle_raw_result = alignment_results.get('needle_raw_result', '')
        if not needle_raw_result:
            return render_template('error.html', message='未找到needle比对结果'), 400
        
        # 创建txt文件在内存中
        import io
        buffer = io.BytesIO()
        buffer.write(needle_raw_result.encode('utf-8'))
        buffer.seek(0)
        
        # 返回文件下载
        return send_file(
            buffer,
            as_attachment=True,
            download_name='needle比对结果.txt',
            mimetype='text/plain'
        )
    except Exception as e:
        app.logger.error(f'Needle download error: {str(e)}')
        return render_template('error.html', message=f'下载失败：{str(e)}'), 500


@app.route('/sirna/upload', methods=['POST'])
def sirna_upload():
    """siRNA工具文件上传处理"""
    try:
        # 确保上传文件夹存在
        sirna_upload_folder = os.path.join('static', 'sirna_uploads')
        os.makedirs(sirna_upload_folder, exist_ok=True)

        # 处理Excel文件
        if 'excel_file' not in request.files:
            return jsonify({'status': 'error', 'message': '未选择Excel文件'})

        excel_file = request.files['excel_file']
        if excel_file.filename == '':
            return jsonify({'status': 'error', 'message': '未选择Excel文件'})

        # 保存Excel文件
        excel_filename = secure_filename(excel_file.filename)
        excel_path = os.path.join(sirna_upload_folder, excel_filename)
        excel_file.save(excel_path)

        # 处理FASTA文件
        fasta_paths = []
        if 'fasta_files' in request.files:
            fasta_files = request.files.getlist('fasta_files')
            for fasta_file in fasta_files:
                if fasta_file.filename != '':
                    fasta_filename = secure_filename(fasta_file.filename)
                    fasta_path = os.path.join(
                        sirna_upload_folder, fasta_filename
                    )
                    fasta_file.save(fasta_path)
                    fasta_paths.append(fasta_path)

        # 保存文件信息到session
        session['sirna_excel_path'] = excel_path
        session['sirna_fasta_paths'] = fasta_paths
        session['sirna_output_filename'] = request.form.get(
            'output_filename', 'siRNA_匹配结果'
        )
        # 保存错配数量参数到session
        session['sirna_mismatch_count'] = int(request.form.get('mismatch_count', 1))

        # 解析文件进行预览
        query_seqs, target_sequence = sirna_analysis.parse_sequences_from_excel(
            excel_path, 
            preview_mode=True
        )
        fasta_sequences, fasta_names = sirna_analysis.parse_sequences_from_fasta(fasta_paths)

        # 生成预览信息
        preview_text = f"Excel文件：{excel_filename}\n"
        preview_text += f"查询序列数量：{len(query_seqs)}\n"
        
        # 显示Excel靶序列信息
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
        app.logger.error(f'siRNA file upload error: {str(e)}')
        return jsonify({'status': 'error', 'message': f'文件上传失败：{str(e)}'})


@app.route('/sirna/analyze', methods=['POST'])
def sirna_analyze():
    """siRNA工具分析处理"""
    try:
        # 从session获取文件路径
        excel_path = session.get('sirna_excel_path')
        fasta_paths = session.get('sirna_fasta_paths', [])
        output_filename = session.get('sirna_output_filename', 'siRNA_匹配结果')

        if not excel_path or not os.path.exists(excel_path):
            return jsonify({'status': 'error', 'message': 'Excel文件不存在'})

        # 获取错配数量参数
        mismatch_count = session.get('sirna_mismatch_count', 1)
        
        # 执行siRNA分析（仅序列匹配部分）
        front_end_results, output_path, target_seq = sirna_analysis.perform_sirna_analysis(
            excel_path, 
            fasta_paths, 
            output_filename,
            mismatch_count
        )

        # 保存结果路径到session
        session['sirna_results_path'] = output_path

        # 生成表格HTML（只显示有FASTA匹配的结果）
        table_html = sirna_analysis.generate_results_table(front_end_results, max_rows=10)

        # 过滤只显示有FASTA匹配的结果（排除'无'的情况）
        filtered_results = [r for r in front_end_results if r.get('fasta_ids') and r['fasta_ids'][0] != '无']
        
        # 启动异步BLAST搜索任务
        blast_task = blast_search_task.delay(target_seq)
        
        # 保存任务ID到session
        session['blast_task_id'] = blast_task.id
        app.logger.info(f'Started BLAST search task with ID: {blast_task.id}')

        # 处理BLAST结果的初始状态，显示正在连接NCBI
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
        app.logger.error(f'siRNA analysis error: {str(e)}')
        import traceback
        app.logger.error(f'siRNA analysis traceback: {traceback.format_exc()}')
        return jsonify({'status': 'error', 'message': f'分析失败：{str(e)}'})


@app.route('/sirna/blast_status/<task_id>')
def blast_status(task_id):
    """查询BLAST搜索任务状态的接口"""
    try:
        task = blast_search_task.AsyncResult(task_id)
        
        if task.state == 'PENDING':
            # 任务已提交但尚未开始
            response = {
                'state': task.state,
                'status': '正连接NCBI验证靶序列...',
                'blast_results': None
            }
        elif task.state == 'PROGRESS':
            # 任务正在进行中
            response = {
                'state': task.state,
                'status': '正连接NCBI验证靶序列...',
                'blast_results': None
            }
        elif task.state == 'SUCCESS':
            # 任务成功完成，解析结果
            blast_results = task.result
            
            # 生成BLAST结果的HTML
            blast_html = '<table class="blast-table">'
            blast_html += '<thead><tr>'
            blast_html += '<th>NCBI ID</th>'
            blast_html += '<th>描述</th>'
            blast_html += '<th>匹配长度</th>'
            blast_html += '<th>一致性(%)</th>'
            blast_html += '<th>E值</th>'
            blast_html += '</tr></thead><tbody>'
            
            for blast_result in blast_results[:2]:  # 只显示前2个结果
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
            
            response = {
                'state': task.state,
                'status': '验证完成',
                'blast_results': blast_html
            }
        elif task.state == 'FAILURE':
            # 任务执行失败
            response = {
                'state': task.state,
                'status': f'验证失败: {str(task.info)}',
                'blast_results': None
            }
        else:
            # 其他状态
            response = {
                'state': task.state,
                'status': f'任务状态: {task.state}',
                'blast_results': None
            }
        
        return jsonify(response)
    except Exception as e:
        app.logger.error(f'Error checking BLAST task status: {str(e)}')
        return jsonify({
            'state': 'ERROR',
            'status': f'获取验证状态失败: {str(e)}',
            'blast_results': None
        }), 500


@app.route('/sirna/download')
def sirna_download():
    """下载siRNA分析结果"""
    try:
        results_path = session.get('sirna_results_path')
        excel_path = session.get('sirna_excel_path')
        fasta_paths = session.get('sirna_fasta_paths', [])

        if not results_path or not os.path.exists(results_path):
            flash('⚠️ 结果文件不存在', 'error')
            return redirect(url_for('sirna_index'))

        # 获取文件名
        filename = os.path.basename(results_path)

        # 先将文件内容读取到内存
        import io
        buffer = io.BytesIO()
        with open(results_path, 'rb') as f:
            buffer.write(f.read())
        buffer.seek(0)

        # 清除所有相关文件
        files_to_delete = [results_path, excel_path] + fasta_paths
        for path in files_to_delete:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                    app.logger.info(f'Deleted file: {path}')
                except Exception as e:
                    app.logger.error(f'Failed to delete file {path}: {str(e)}')

        # 清除session中的相关数据
        session.pop('sirna_results_path', None)
        session.pop('sirna_excel_path', None)
        session.pop('sirna_fasta_paths', None)
        session.pop('sirna_output_filename', None)
        session.pop('blast_task_id', None)  # 同时清除BLAST任务ID
        app.logger.info('Cleared session data after siRNA download')

        # 返回文件
        excel_mimetype = 'application/vnd.ms-excel'
        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype=excel_mimetype
        )

    except Exception as e:
        app.logger.error(f'siRNA download error: {str(e)}')
        flash(f'⚠️ 下载失败：{str(e)}', 'error')
        return redirect(url_for('sirna_index'))


@app.route('/download_template')
def download_template():
    template_path = 'static/templates/template.xlsx'
    if not os.path.exists(template_path):
        flash('⚠️ 模板文件未找到', 'error')
        return redirect(url_for('st26_index'))
    return send_file(
        template_path,
        as_attachment=True,
        download_name='template.xlsx'
    )


@app.route('/upload', methods=['POST'])
def upload_file():
    app.logger.info('Received file upload request')
    if 'file' not in request.files:
        app.logger.warning('No file found in upload request')
        flash(
            '⚠️ 未选择文件',
            'error'
        )
        return redirect(url_for('st26_index'))

    file = request.files['file']
    if file.filename == '':
        app.logger.warning('Empty filename in upload request')
        flash('⚠️ 未选择文件', 'error')
        return redirect(url_for('st26_index'))

    if file and file.filename.endswith('.xlsx'):
        # 使用UUID生成唯一文件名
        unique_filename = (
            f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
        )
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        app.logger.info(f'File saved successfully: {file_path}')

        try:
            # 提交异步转换任务
            task = convert_excel_task.apply_async(
                args=[file_path, app.config['OUTPUTS_FOLDER']]
            )
            app.logger.info(f'Async task submitted with ID: {task.id}')

            # 保存任务信息到session
            session['task_id'] = task.id
            session['uploaded_file_path'] = file_path  # 存储上传的文件路径
            session['original_filename'] = file.filename  # 存储原始文件名

            # 清除之前的结果和错误信息
            session.pop('xml_file', None)
            session.pop('sequence_summary', None)
            session.pop('reminders', None)
            session.pop('error_message', None)
            session.pop('error_sequence', None)
            session.pop('error_position', None)

            # 不再使用flash显示"文件正在转换中"消息，改为在前端JavaScript中处理
        except Exception as e:
            # 删除上传的文件
            if os.path.exists(file_path):
                os.remove(file_path)
            app.logger.error(f'Error submitting task: {str(e)}')
            flash(f'⚠️ 提交转换任务出错: {str(e)}。数据文件已经删除，请稍后重试。', 'error')
            return redirect(url_for('st26_index'))

        return redirect(url_for('st26_index'))
    else:
        app.logger.warning(f'Invalid file format: {file.filename}')
        flash('⚠️ 文件格式不正确，请上传 .xlsx 文件', 'error')
        return redirect(url_for('st26_index'))


@app.route('/task_status/<task_id>')
def task_status(task_id):
    """查询异步任务状态的接口"""
    app.logger.info(f'Checking status for task: {task_id}')
    try:
        task = convert_excel_task.AsyncResult(task_id)

        # 优化任务状态检查，避免404错误
        # 不再尝试直接检查任务是否存在，而是让Celery自己处理
        # 对所有请求都返回200状态码，在JSON中包含错误信息
        try:
            # 尝试获取任务状态，捕获可能的异常
            task_state = task.state
        except Exception as e:
            # 如果获取任务状态失败，返回错误信息
            app.logger.warning(f'Error checking task {task_id} state: {str(e)}')
            return jsonify({
                'state': 'ERROR',
                'current': 0,
                'total': 100,
                'status': f'获取任务状态失败: {str(e)}',
                'error': str(e)
            })

        if task.state == 'PENDING':
            # 任务已提交但尚未开始
            response = {
                'state': task.state,
                'current': 0,
                'total': 100,
                'status': '任务已提交，等待处理...'
            }
        elif task.state == 'PROGRESS':
            # 任务正在进行中
            response = {
                'state': task.state,
                'current': task.info.get('current', 0),
                'total': task.info.get('total', 100),
                'status': '转换进行中...'
            }
        elif task.state == 'SUCCESS':
            # 任务成功完成
            try:
                result = task.result

                # 处理不同格式的结果
                
                if (isinstance(result, (tuple, list)) and len(result) == 3):
                    # 结果是一个元组或列表，直接使用
                    xml_file, sequence_summary, reminders = result

                    # 保存转换结果到session（直接使用字典格式）
                    session['xml_file'] = xml_file
                    session['sequence_summary'] = sequence_summary
                    session['reminders'] = reminders

                    response = {
                        'state': task.state,
                        'current': 100,
                        'total': 100,
                        'status': '转换完成！',
                        'result': {
                            'status': 'success',
                            'xml_file': xml_file,
                            'sequence_summary': sequence_summary,
                            'reminders': reminders
                        }
                    }
                elif isinstance(result, dict) and 'status' in result:
                    # 结果是一个字典，包含status键
                    if result['status'] == 'success':
                        # 保存转换结果到session（直接使用字典格式）
                        session['xml_file'] = result['xml_file']
                        session['sequence_summary'] = result['sequence_summary']
                        session['reminders'] = result['reminders']

                        response = {
                            'state': task.state,
                            'current': 100,
                            'total': 100,
                            'status': '转换完成！',
                            'result': result
                        }
                    else:
                        # 转换过程中出错
                        error_msg = result.get('error_message', '未知错误')

                        # 删除上传的文件
                        uploaded_file_path = (
                            session.pop('uploaded_file_path', None)
                        )
                        if uploaded_file_path and (
                            os.path.exists(uploaded_file_path)
                        ):
                            os.remove(uploaded_file_path)

                        # 清除任务信息
                        session.pop('task_id', None)
                        session.pop('original_filename', None)

                        response = {
                            'state': 'FAILURE',
                            'current': 100,
                            'total': 100,
                            'status': f'转换失败: {error_msg}。数据文件已经删除，请修改后重新上传。',
                            'error': error_msg
                        }
                else:
                    # 结果格式不符合预期
                    error_msg = f'转换结果格式错误: {str(result)}'
                    response = {
                        'state': 'FAILURE',
                        'current': 100,
                        'total': 100,
                        'status': f'转换失败: {error_msg}。数据文件已经删除，请修改后重新上传。',
                        'error': error_msg
                    }

                    # 删除上传的文件
                    uploaded_file_path = (
                        session.pop('uploaded_file_path', None)
                    )
                    if uploaded_file_path and (
                        os.path.exists(uploaded_file_path)
                    ):
                        os.remove(uploaded_file_path)

                    # 清除任务信息
                    session.pop('task_id', None)
                    session.pop('original_filename', None)
            except Exception as e:
                # 处理结果解析错误
                error_msg = f'解析转换结果出错: {str(e)}'
                response = {
                    'state': 'FAILURE',
                    'current': 100,
                    'total': 100,
                    'status': f'转换失败: {error_msg}。数据文件已经删除，请修改后重新上传。',
                    'error': error_msg
                }

                # 删除上传的文件
                uploaded_file_path = session.pop('uploaded_file_path', None)
                if uploaded_file_path and os.path.exists(uploaded_file_path):
                    os.remove(uploaded_file_path)

                # 清除任务信息
                session.pop('task_id', None)
                session.pop('original_filename', None)
        elif task.state == 'FAILURE':
            # 任务执行失败
            error_msg = str(task.info) if task.info else '未知错误'
            app.logger.error(f'Task {task_id} failed: {error_msg}')

            # 删除上传的文件
            uploaded_file_path = session.pop('uploaded_file_path', None)
            if uploaded_file_path and os.path.exists(uploaded_file_path):
                os.remove(uploaded_file_path)
                app.logger.info(f'Deleted uploaded file: {uploaded_file_path}')

            # 清除任务信息
            session.pop('task_id', None)
            session.pop('original_filename', None)

            response = {
                'state': task.state,
                'current': 100,
                'total': 100,
                'status': f'任务执行失败: {error_msg}。数据文件已经删除，请修改后重新上传。',
                'error': error_msg
            }
        else:
            # 其他状态
            response = {
                'state': task.state,
                'current': 0,
                'total': 100,
                'status': f'任务状态: {task.state}'
            }

        return jsonify(response)
    except Exception as e:
        # 处理所有异常，确保返回JSON响应，避免前端404错误
        return jsonify({
            'state': 'ERROR',
            'current': 0,
            'total': 100,
            'status': f'获取任务状态失败: {str(e)}',
            'error': str(e)
        })  # 返回200状态码，避免前端HTTP错误


@app.route('/download_xml/<filename>')
def download_xml(filename):
    app.logger.info(f'Request to download XML: {filename}')
    xml_path = os.path.join(app.config['OUTPUTS_FOLDER'], filename)
    if not os.path.exists(xml_path):
        app.logger.warning(f'XML file not found: {xml_path}')
        flash('⚠️ XML 文件未找到', 'error')
        return redirect(url_for('st26_index'))

    # 先获取文件内容用于下载
    import io
    buffer = io.BytesIO()
    with open(xml_path, 'rb') as f:
        buffer.write(f.read())
    buffer.seek(0)

    # 删除上传的Excel文件和生成的XML文件
    try:
        # 删除生成的XML文件
        if os.path.exists(xml_path):
            os.remove(xml_path)
            app.logger.info(f'Deleted XML file: {xml_path}')

        # 删除上传的Excel文件
        uploaded_file_path = session.pop('uploaded_file_path', None)
        if uploaded_file_path and os.path.exists(uploaded_file_path):
            os.remove(uploaded_file_path)
            app.logger.info(
                        f'Deleted uploaded Excel file: {uploaded_file_path}'
                    )

        # 清除session中的缓存数据
        session.pop('xml_file', None)
        session.pop('sequence_summary', None)
        session.pop('reminders', None)
        session.pop('task_id', None)
        session.pop('original_filename', None)
        app.logger.info('Cleared session data after download')
    except Exception as e:
        flash(f'清理临时文件时出错: {str(e)}', 'warning')

    # 返回文件内容
    return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='text/xml'
        )


@app.route('/clear_task/<task_id>', methods=['GET', 'POST'])
def clear_task(task_id):
    """清除任务信息的接口"""
    try:
        # 删除上传的文件
        uploaded_file_path = session.pop('uploaded_file_path', None)
        if uploaded_file_path and os.path.exists(uploaded_file_path):
            os.remove(uploaded_file_path)

        # 清除session中的任务信息
        session.pop('task_id', None)
        session.pop('original_filename', None)
        session.pop('xml_file', None)
        session.pop('sequence_summary', None)
        session.pop('reminders', None)
        session.pop('error_message', None)
        session.pop('error_sequence', None)
        session.pop('error_position', None)

        return jsonify({'status': 'success', 'message': '任务信息已清除'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@celery.task(bind=True)
def convert_excel_task(self, file_path, output_folder):
    """异步转换Excel为XML的Celery任务"""
    app.logger.info(f'Starting conversion task for file: {file_path}')
    try:
        # 设置任务状态
        self.update_state(state='PROGRESS', meta={'current': 0, 'total': 100})

        # 执行转换
        xml_file_name, sequence_summary, reminders = (
            convert_excel_to_xml(file_path, output_folder)
        )
        app.logger.info(
            f'Conversion completed successfully, generated XML: '
            f'{xml_file_name}'
        )

        # 直接返回元组，与task_status路由的预期格式一致
        return xml_file_name, sequence_summary, reminders
    except Exception as e:
        app.logger.error(
            f'Conversion task failed: {str(e)}',
            exc_info=True
        )
        return {
            'status': 'error',
            'error_message': str(e)
        }


@celery.task(bind=True)
def blast_search_task(self, target_sequence):
    """异步执行BLAST搜索的Celery任务"""
    app.logger.info(f'Starting BLAST search for target sequence')
    try:
        # 设置任务状态
        self.update_state(state='PROGRESS', meta={'current': 0, 'total': 100})
        
        # 导入所需模块
        from Bio.Blast import NCBIWWW
        from Bio.Blast import NCBIXML
        
        # 执行BLAST搜索
        result_handle = NCBIWWW.qblast(
            program='blastn',
            database='nt',
            sequence=target_sequence,
            expect=0.01,
            hitlist_size=5
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
        
        app.logger.info(f'BLAST search completed, found {len(blast_results)} matches')
        
        # 关闭结果句柄
        try:
            result_handle.close()
        except:
            pass
            
        return blast_results
        
    except Exception as e:
        app.logger.error(f'BLAST search task failed: {str(e)}', exc_info=True)
        return []


if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    app.run(debug=True, port=port)

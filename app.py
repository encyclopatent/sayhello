from flask import Flask, render_template, request, flash, redirect, url_for, send_file, session, jsonify
import os
import uuid
from werkzeug.utils import secure_filename
from st26autonew import convert_excel_to_xml
from celery import Celery

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 需要设置secret_key以使用flash

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

@app.route('/')
def index():
    xml_file = session.get('xml_file', None)
    sequence_summary = session.get('sequence_summary', None)
    reminders = session.get('reminders', None)
    return render_template('index.html', xml_file=xml_file, sequence_summary=sequence_summary, reminders=reminders)

@app.route('/download_template')
def download_template():
    template_path = 'static/templates/template.xlsx'
    if not os.path.exists(template_path):
        flash('⚠️ 模板文件未找到', 'error')
        return redirect(url_for('index'))
    return send_file(template_path, as_attachment=True, attachment_filename='template.xlsx')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('⚠️ 未选择文件', 'error')
        return redirect(url_for('index'))
    
    file = request.files['file']
    if file.filename == '':
        flash('⚠️ 未选择文件', 'error')
        return redirect(url_for('index'))
    
    if file and file.filename.endswith('.xlsx'):
        # 使用UUID生成唯一文件名
        unique_filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        
        try:
            # 提交异步转换任务
            task = convert_excel_task.apply_async(args=[file_path, app.config['OUTPUTS_FOLDER']])
            
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
            flash(f'⚠️ 提交转换任务出错: {str(e)}。数据文件已经删除，请稍后重试。', 'error')
            return redirect(url_for('index'))
        
        return redirect(url_for('index'))
    else:
        flash('⚠️ 文件格式不正确，请上传 .xlsx 文件', 'error')
        return redirect(url_for('index'))

@app.route('/task_status/<task_id>')
def task_status(task_id):
    """查询异步任务状态的接口"""
    try:
        task = convert_excel_task.AsyncResult(task_id)
        
        # 检查任务是否存在（Celery对无效task_id会返回PENDING状态）
        # 通过检查任务的backend是否有记录来判断
        task_exists = task.backend.get(task.backend.get_key_for_task(task.id)) is not None
        
        if not task_exists:
            # 任务ID无效
            return jsonify({
                'state': 'ERROR',
                'current': 0,
                'total': 100,
                'status': f'无效的任务ID: {task_id}',
                'error': f'无效的任务ID: {task_id}'
            }), 404
        
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
                    
                    # 保存转换结果到session
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
                        # 保存转换结果到session
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
                        uploaded_file_path = session.pop('uploaded_file_path', None)
                        if uploaded_file_path and os.path.exists(uploaded_file_path):
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
                    uploaded_file_path = session.pop('uploaded_file_path', None)
                    if uploaded_file_path and os.path.exists(uploaded_file_path):
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
            
            # 删除上传的文件
            uploaded_file_path = session.pop('uploaded_file_path', None)
            if uploaded_file_path and os.path.exists(uploaded_file_path):
                os.remove(uploaded_file_path)
                
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
        # 处理所有异常，确保返回JSON响应
        return jsonify({
            'state': 'ERROR',
            'current': 0,
            'total': 100,
            'status': f'获取任务状态失败: {str(e)}',
            'error': str(e)
        }), 500

@app.route('/download_xml/<filename>')
def download_xml(filename):
    xml_path = os.path.join(app.config['OUTPUTS_FOLDER'], filename)
    if not os.path.exists(xml_path):
        flash('⚠️ XML 文件未找到', 'error')
        return redirect(url_for('index'))
    
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
        
        # 删除上传的Excel文件
        uploaded_file_path = session.pop('uploaded_file_path', None)
        if uploaded_file_path and os.path.exists(uploaded_file_path):
            os.remove(uploaded_file_path)
        
        # 清除session中的缓存数据
        session.pop('xml_file', None)
        session.pop('sequence_summary', None)
        session.pop('reminders', None)
        session.pop('task_id', None)
        session.pop('original_filename', None)
    except Exception as e:
        flash(f'清理临时文件时出错: {str(e)}', 'warning')
    
    # 返回文件内容
    return send_file(buffer, as_attachment=True, attachment_filename=filename, mimetype='text/xml')

@app.route('/clear_task/<task_id>')
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
    try:
        # 设置任务状态
        self.update_state(state='PROGRESS', meta={'current': 0, 'total': 100})
        
        # 执行转换
        xml_file_name, sequence_summary, reminders = convert_excel_to_xml(file_path, output_folder)
        
        # 直接返回元组，与task_status路由的预期格式一致
        return xml_file_name, sequence_summary, reminders
    except Exception as e:
        return {
            'status': 'error',
            'error_message': str(e)
        }

if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    app.run(debug=True, port=port)

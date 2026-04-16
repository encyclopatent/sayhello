"""ST26 XML conversion routes."""
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, make_response, flash, send_file as flask_send_file, current_app
from werkzeug.utils import secure_filename
import os
import uuid
import json
import io
import openpyxl
import flask

st26_bp = Blueprint('st26', __name__, url_prefix='/st26')


def send_file_compat(*args, **kwargs):
    """Flask 版本兼容的 send_file 包装器"""
    # 尝试使用 attachment_filename，如果不支持则使用 download_name
    attachment_filename = kwargs.pop('attachment_filename', None)
    if attachment_filename:
        kwargs['download_name'] = attachment_filename
    return flask_send_file(*args, **kwargs)


@st26_bp.route('/guide')
def guide():
    """ST26 usage guide page."""
    return render_template('st26_guide.html')


@st26_bp.route('/')
def index():
    """ST26 tool main page."""
    response = make_response()
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'

    is_new_navigation = request.args.get('new', 'false').lower() == 'true'

    xml_file = session.get('xml_file', None)
    sequence_summary = session.get('sequence_summary', None)
    reminders = session.get('reminders', None)
    task_id = session.get('task_id', None)
    original_filename = session.get('original_filename', None)
    error_message = session.get('error_message', None)
    error_sequence = session.get('error_sequence', None)
    error_position = session.get('error_position', None)

    if is_new_navigation:
        if xml_file or task_id or error_message:
            session.clear()
            xml_file = sequence_summary = reminders = task_id = original_filename = error_message = error_sequence = error_position = None
    else:
        if xml_file and task_id:
            task_id = None

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


@st26_bp.route('/upload', methods=['POST'])
def upload():
    """Handle file upload for ST26 conversion."""
    from tasks import convert_excel_task

    if 'file' not in request.files:
        flash('⚠️ 未选择文件', 'error')
        return redirect(url_for('st26.index'))

    file = request.files['file']
    if file.filename == '':
        flash('⚠️ 未选择文件', 'error')
        return redirect(url_for('st26.index'))

    if not file.filename.endswith('.xlsx'):
        flash('⚠️ 文件格式不正确，请上传 .xlsx 文件', 'error')
        return redirect(url_for('st26.index'))

    upload_folder = os.path.normpath(current_app.config['UPLOAD_FOLDER'])
    secure_name = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4().hex}_{secure_name}"
    unique_filename = os.path.basename(unique_filename)

    if not unique_filename or unique_filename.startswith('.'):
        flash('⚠️ 文件名不合法', 'error')
        return redirect(url_for('st26.index'))

    file_path = os.path.join(upload_folder, unique_filename)
    file_path = os.path.normpath(file_path)
    if not file_path.startswith(upload_folder):
        flash('⚠️ 文件路径不合法', 'error')
        return redirect(url_for('st26.index'))

    # Validate Excel content
    try:
        file.seek(0)
        test_wb = openpyxl.load_workbook(file, read_only=True)
        test_wb.close()
    except Exception as e:
        flash('⚠️ 文件格式不正确或文件已损坏', 'error')
        return redirect(url_for('st26.index'))

    file.seek(0)
    file.save(file_path)

    # Handle expert settings
    expert_settings = None
    try:
        expert_settings_json = request.form.get('expert_settings')
        if expert_settings_json:
            expert_settings = json.loads(expert_settings_json)
            session['expert_settings'] = expert_settings
    except Exception:
        pass

    # Submit Celery task
    try:
        task = convert_excel_task.apply_async(
            args=[file_path, current_app.config['OUTPUTS_FOLDER'], expert_settings]
        )
        session['task_id'] = task.id
        session['uploaded_filename'] = unique_filename
        session['original_filename'] = file.filename

        session.pop('xml_file', None)
        session.pop('sequence_summary', None)
        session.pop('reminders', None)
        session.pop('error_message', None)
        session.pop('error_sequence', None)
        session.pop('error_position', None)

        return redirect(url_for('st26.result', task_id=task.id))
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        flash(f'⚠️ 提交转换任务出错: {str(e)}', 'error')
        return redirect(url_for('st26.index'))


@st26_bp.route('/result')
def result():
    """Display conversion result page."""
    task_id = request.args.get('task_id')
    if not task_id:
        return redirect(url_for('st26.index'))

    try:
        from tasks import convert_excel_task
        task = convert_excel_task.AsyncResult(task_id)
        task_state = task.state

        if task_state in ['PENDING', 'PROGRESS']:
            session.pop('xml_file', None)
            session.pop('sequence_summary', None)
            session.pop('reminders', None)
            session.pop('error_message', None)
            session.pop('error_sequence', None)
            session.pop('error_position', None)
    except Exception:
        pass

    xml_file = session.get('xml_file')
    sequence_summary = session.get('sequence_summary')
    reminders = session.get('reminders')

    return render_template('result.html',
                          task_id=task_id,
                          xml_file=xml_file,
                          sequence_summary=sequence_summary,
                          reminders=reminders)


@st26_bp.route('/download/<filename>')
def download(filename):
    """Download generated XML file."""
    from utils.security import get_uploaded_file_path

    xml_path = os.path.join(current_app.config['OUTPUTS_FOLDER'], filename)
    if not os.path.exists(xml_path):
        flash('⚠️ XML 文件未找到', 'error')
        return redirect(url_for('st26.index'))

    buffer = io.BytesIO()
    with open(xml_path, 'rb') as f:
        buffer.write(f.read())
    buffer.seek(0)

    try:
        if os.path.exists(xml_path):
            os.remove(xml_path)

        uploaded_filename = session.pop('uploaded_filename', None)
        if uploaded_filename:
            try:
                upload_folder = current_app.config['UPLOAD_FOLDER']
                uploaded_file_path = get_uploaded_file_path(upload_folder, uploaded_filename)
                if os.path.exists(uploaded_file_path):
                    os.remove(uploaded_file_path)
            except (ValueError, OSError):
                pass

        session.pop('xml_file', None)
        session.pop('sequence_summary', None)
        session.pop('reminders', None)
        session.pop('task_id', None)
        session.pop('original_filename', None)
    except Exception as e:
        flash(f'清理临时文件时出错: {str(e)}', 'warning')

    return send_file_compat(
        buffer,
        as_attachment=True,
        attachment_filename=filename,
        mimetype='text/xml'
    )


@st26_bp.route('/template')
def template():
    """Download template file."""
    template_path = 'static/templates/template.xlsx'
    if not os.path.exists(template_path):
        flash('⚠️ 模板文件未找到', 'error')
        return redirect(url_for('st26.index'))
    return send_file_compat(
        template_path,
        as_attachment=True,
        attachment_filename='template.xlsx'
    )


@st26_bp.route('/clear_task/<task_id>', methods=['GET', 'POST'])
def clear_task(task_id):
    """Clear task information."""
    from utils.security import get_uploaded_file_path
    from tasks import convert_excel_task

    try:
        task = convert_excel_task.AsyncResult(task_id)
        task_state = task.state

        if task_state == 'SUCCESS':
            session.pop('task_id', None)
            session.pop('uploaded_filename', None)
            session.pop('original_filename', None)
            session.pop('error_message', None)
            session.pop('error_sequence', None)
            session.pop('error_position', None)

        elif task_state in ['PENDING', 'STARTED', 'RETRY']:
            uploaded_filename = session.pop('uploaded_filename', None)
            if uploaded_filename:
                try:
                    upload_folder = current_app.config['UPLOAD_FOLDER']
                    uploaded_file_path = get_uploaded_file_path(upload_folder, uploaded_filename)
                    if os.path.exists(uploaded_file_path):
                        os.remove(uploaded_file_path)
                except (ValueError, OSError):
                    pass

            current_app.celery.control.revoke(task_id, terminate=True)
            session.pop('task_id', None)
            session.pop('original_filename', None)
            session.pop('xml_file', None)
            session.pop('sequence_summary', None)
            session.pop('reminders', None)
            session.pop('error_message', None)
            session.pop('error_sequence', None)
            session.pop('error_position', None)

        elif task_state in ['FAILURE', 'REVOKED']:
            uploaded_filename = session.pop('uploaded_filename', None)
            if uploaded_filename:
                try:
                    upload_folder = current_app.config['UPLOAD_FOLDER']
                    uploaded_file_path = get_uploaded_file_path(upload_folder, uploaded_filename)
                    if os.path.exists(uploaded_file_path):
                        os.remove(uploaded_file_path)
                except (ValueError, OSError):
                    pass

            session.pop('task_id', None)
            session.pop('original_filename', None)
            session.pop('xml_file', None)
            session.pop('sequence_summary', None)
            session.pop('reminders', None)
            session.pop('error_message', None)
            session.pop('error_sequence', None)
            session.pop('error_position', None)

        else:
            session.pop('task_id', None)

        return '', 204
    except Exception:
        return '', 500


@st26_bp.route('/clear_all', methods=['GET', 'POST'])
def clear_all():
    """Clear all task data."""
    from utils.security import get_uploaded_file_path

    try:
        task_id = session.get('task_id')
        if task_id:
            uploaded_filename = session.get('uploaded_filename')
            if uploaded_filename:
                try:
                    upload_folder = current_app.config['UPLOAD_FOLDER']
                    uploaded_file_path = get_uploaded_file_path(upload_folder, uploaded_filename)
                    if os.path.exists(uploaded_file_path):
                        os.remove(uploaded_file_path)
                except (ValueError, OSError):
                    pass

        session.clear()

        if request.method == 'POST':
            return '', 204
        return jsonify({'status': 'success', 'message': '所有数据已清除'})
    except Exception:
        return '', 500


@st26_bp.route('/xml_info')
def xml_info():
    """Get XML file information."""
    task_id = request.args.get('task_id')
    if not task_id:
        return jsonify({'status': 'error', 'message': '未提供任务ID'}), 400

    session_task_id = session.get('task_id')
    xml_file = session.get('xml_file', None)
    error_message = session.get('error_message', None)

    if xml_file:
        return jsonify({
            'status': 'success',
            'xml_file': xml_file,
            'sequence_summary': session.get('sequence_summary', None),
            'reminders': session.get('reminders', None)
        })
    elif error_message:
        return jsonify({'status': 'error', 'message': error_message})
    elif not session_task_id or task_id != session_task_id:
        return jsonify({'status': 'error', 'message': '未找到当前任务的结果信息'})
    else:
        return jsonify({'status': 'error', 'message': '未找到XML文件信息'})


@st26_bp.route('/task_status/<task_id>')
def task_status(task_id):
    """Check Celery task status."""
    from utils.security import get_uploaded_file_path
    from tasks import convert_excel_task

    try:
        task = convert_excel_task.AsyncResult(task_id)

        response = {
            'state': task.state,
            'current': 0,
            'total': 100,
            'status': '处理中...',
            'stage': '',
            'processed_sequences': 0,
            'total_sequences': 0
        }

        if task.state == 'PENDING':
            response['status'] = '正在排队...'
        elif task.state == 'PROGRESS':
            response.update(task.info)
            if 'stage' not in response:
                response['stage'] = task.info.get('stage', '处理中...')
        elif task.state == 'SUCCESS':
            response['status'] = '处理完成'
            response['current'] = 100
            response['total'] = 100

            if 'xml_file' not in session:
                try:
                    result = task.result
                    if isinstance(result, (tuple, list)) and len(result) >= 2:
                        xml_file = result[0]
                        sequence_summary = result[1]
                        # Handle both 2-element and 3-element tuples
                        if len(result) == 3:
                            reminders = result[2]
                        else:
                            # Extract reminder count from summary
                            reminders = sequence_summary.get('reminder_count', 0)
                        session['xml_file'] = xml_file
                        session['sequence_summary'] = sequence_summary
                        session['reminders'] = reminders
                        session.pop('task_id', None)
                    elif isinstance(result, dict) and result.get('status') == 'success':
                        session['xml_file'] = result['xml_file']
                        session['sequence_summary'] = result['sequence_summary']
                        session['reminders'] = result.get('reminders', 0)
                        session.pop('task_id', None)
                    else:
                        error_msg = f'转换结果格式错误: {str(result)}'
                        uploaded_filename = session.pop('uploaded_filename', None)
                        if uploaded_filename:
                            try:
                                upload_folder = current_app.config['UPLOAD_FOLDER']
                                uploaded_file_path = get_uploaded_file_path(upload_folder, uploaded_filename)
                                if os.path.exists(uploaded_file_path):
                                    os.remove(uploaded_file_path)
                            except (ValueError, OSError):
                                pass
                        session.pop('task_id', None)
                        session.pop('original_filename', None)
                        response = {'state': 'FAILURE', 'status': f'转换失败: {error_msg}', 'error': error_msg}
                except Exception as e:
                    error_msg = f'解析转换结果出错: {str(e)}'
                    uploaded_filename = session.pop('uploaded_filename', None)
                    if uploaded_filename:
                        try:
                            upload_folder = current_app.config['UPLOAD_FOLDER']
                            uploaded_file_path = get_uploaded_file_path(upload_folder, uploaded_filename)
                            if os.path.exists(uploaded_file_path):
                                os.remove(uploaded_file_path)
                        except (ValueError, OSError):
                            pass
                    session.pop('task_id', None)
                    response = {'state': 'FAILURE', 'status': f'转换失败: {error_msg}', 'error': error_msg}

        elif task.state == 'FAILURE':
            response['status'] = '失败'
            task_info = task.info
            if isinstance(task_info, dict):
                response['error'] = task_info.get('error_message', str(task_info))
            else:
                response['error'] = str(task_info)

            uploaded_filename = session.pop('uploaded_filename', None)
            if uploaded_filename:
                try:
                    upload_folder = current_app.config['UPLOAD_FOLDER']
                    uploaded_file_path = get_uploaded_file_path(upload_folder, uploaded_filename)
                    if os.path.exists(uploaded_file_path):
                        os.remove(uploaded_file_path)
                except (ValueError, OSError):
                    pass
            session.pop('task_id', None)
            session.pop('original_filename', None)

        return jsonify(response)
    except Exception as e:
        return jsonify({'state': 'ERROR', 'status': f'查询出错: {str(e)}'})

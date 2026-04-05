"""Fragment analysis routes."""
from flask import Blueprint, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import os

fragment_bp = Blueprint('fragment', __name__, url_prefix='/fragment')


@fragment_bp.route('/')
def index():
    """Fragment tool main page."""
    return render_template('fragment.html')


@fragment_bp.route('/process', methods=['POST'])
def process():
    """Handle fragment analysis request."""
    try:
        upload_folder = os.path.join('static', 'fragment_uploads')
        output_folder = os.path.join('static', 'fragment_outputs')
        os.makedirs(upload_folder, exist_ok=True)
        os.makedirs(output_folder, exist_ok=True)

        if 'excel_file' not in request.files:
            return jsonify({'status': 'error', 'message': '未选择Excel文件'})

        excel_file = request.files['excel_file']
        if excel_file.filename == '':
            return jsonify({'status': 'error', 'message': '未选择Excel文件'})

        filename = secure_filename(excel_file.filename)
        excel_path = os.path.join(upload_folder, filename)
        excel_file.save(excel_path)

        from peptide2fragment import process_compounds as process_fragments
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
        return jsonify({'status': 'error', 'message': f'处理失败：{str(e)}'})


@fragment_bp.route('/download/<path:filename>')
def download(filename):
    """Download fragment analysis result file."""
    try:
        from utils.security import validate_path

        # Validate the filename to prevent path traversal
        output_folder = os.path.join('static', 'fragment_outputs')
        file_path = validate_path(output_folder, filename)

        return send_file(file_path, as_attachment=True)
    except ValueError:
        return jsonify({'status': 'error', 'message': '无效的文件路径'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'下载失败：{str(e)}'})

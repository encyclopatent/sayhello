"""Flask application factory with Blueprint-based route organization."""
import os
import logging
from datetime import datetime
from flask import Flask, session, request, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import blueprints
from routes import main_bp, st26_bp, sirna_bp, fragment_bp, alignment_bp

# Import middleware
from middleware import InputValidationMiddleware

# Import Celery and tasks
from celery_app import celery
import tasks


def create_app():
    """Application factory function."""
    app = Flask(__name__)

    # Apply ProxyFix middleware
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    # Secret key configuration
    app.secret_key = os.environ.get('SECRET_KEY', 'your_secret_key')

    # Debug mode
    app.debug = os.environ.get('DEBUG', 'False').lower() == 'true'

    # Max content length (16MB default)
    app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get('MAX_CONTENT_LENGTH', 16777216))

    # Configure directories
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', os.path.join('static', 'uploads'))
    OUTPUTS_FOLDER = os.environ.get('OUTPUTS_FOLDER', os.path.join('static', 'outputs'))
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(OUTPUTS_FOLDER, exist_ok=True)
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['OUTPUTS_FOLDER'] = OUTPUTS_FOLDER

    # Redis configuration
    redis_host = os.environ.get('REDIS_HOST', 'localhost')
    redis_port = os.environ.get('REDIS_PORT', 6379)
    redis_password = os.environ.get('REDIS_PASSWORD', '')
    redis_db = os.environ.get('REDIS_DB', 0)

    redis_url = f'redis://'
    if redis_password:
        redis_url += f':{redis_password}@'
    redis_url += f'{redis_host}:{redis_port}/{redis_db}'

    # Celery configuration
    # 1. 保留给 Flask（如果其他插件需要）
    app.config['CELERY_BROKER_URL'] = redis_url
    app.config['CELERY_RESULT_BACKEND'] = redis_url
    app.config['CELERY_BROKER_POOL_LIMIT'] = 10
    app.config['CELERY_BROKER_HEARTBEAT'] = 30
    app.config['CELERY_BROKER_CONNECTION_TIMEOUT'] = 20
    app.config['CELERY_RESULT_BACKEND_MAX_RETRIES'] = 3
    app.config['CELERY_RESULT_BACKEND_RETRY_INTERVAL'] = 1

    # 2. 直接用新版小写规范，精准喂给 Celery 实例
    celery.conf.broker_url = redis_url
    celery.conf.result_backend = redis_url

    # Configure logging
    _configure_logging(app)

    # Apply input validation middleware
    InputValidationMiddleware(app)

    # Initialize Celery with app config
    tasks.init_celery(app)

    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(st26_bp)
    app.register_blueprint(sirna_bp)
    app.register_blueprint(fragment_bp)
    app.register_blueprint(alignment_bp)

    # Make celery available at app level
    app.celery = celery

    # Security helper for backward compatibility
    @app.template_global()
    def _get_uploaded_file_path(filename: str) -> str:
        """Safely get uploaded file path."""
        from utils.security import get_uploaded_file_path as utils_get_path
        return utils_get_path(app.config['UPLOAD_FOLDER'], filename)

    # Global clear_all route (accessible from any blueprint)
    @app.route('/clear_all', methods=['GET', 'POST'])
    def clear_all():
        """Clear all session data."""
        try:
            session.clear()
            if request.method == 'POST':
                return '', 204
            return jsonify({'status': 'success', 'message': '所有数据已清除'})
        except Exception:
            return '', 500

    return app


def _configure_logging(app: Flask):
    """Configure application logging."""
    log_dir = os.environ.get('LOG_DIR', 'logs')
    log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    os.makedirs(log_dir, exist_ok=True)

    log_format = logging.Formatter(
        '%(asctime)s - [%(levelname)s] - %(name)s - %(funcName)s:%(lineno)d - %(message)s'
    )

    # File handler
    file_handler = logging.FileHandler(
        f'{log_dir}/app_{datetime.now().strftime("%Y%m%d")}.log'
    )
    file_handler.setLevel(getattr(logging, log_level))
    file_handler.setFormatter(log_format)

    # Security log handler
    security_handler = logging.FileHandler(
        f'{log_dir}/security_{datetime.now().strftime("%Y%m%d")}.log'
    )
    security_handler.setLevel(logging.WARNING)
    security_handler.setFormatter(log_format)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if app.debug else getattr(logging, log_level))
    console_handler.setFormatter(log_format)

    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.addHandler(security_handler)
    app.logger.setLevel(getattr(logging, log_level))


# Create the app instance
app = create_app()


if __name__ == '__main__':
    import sys

    env_port = os.environ.get('PORT')
    if env_port:
        port = int(env_port)
    else:
        port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000

    host = os.environ.get('HOST', '0.0.0.0')

    from werkzeug.serving import make_server
    srv = make_server(host, port, app, threaded=True)
    srv.serve_forever()

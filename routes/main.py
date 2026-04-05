"""Main page routes."""
from flask import Blueprint, render_template

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Main page route."""
    return render_template('main.html')

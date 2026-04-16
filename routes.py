"""
Main Routes
Home page and general routes
"""
from flask import Blueprint, render_template, redirect, url_for, send_from_directory
import os

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Home page"""
    return render_template('index.html')


@main_bp.route('/login')
def login():
    """Generic login page - redirects to login options"""
    return render_template('login.html')


@main_bp.route('/favicon.ico')
def favicon():
    """Return favicon"""
    # For now, return a simple icon or 404 if not found
    return '', 204  # No content response

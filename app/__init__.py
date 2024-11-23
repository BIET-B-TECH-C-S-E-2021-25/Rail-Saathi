# Flask app initialization
import os
import time
from flask import Flask, flash, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from flask_migrate import Migrate
from dotenv import load_dotenv
# from app import db

# Load environment variables
load_dotenv()

# Initialize extensions
db = SQLAlchemy()
csrf = CSRFProtect()
# Initialize the Migrate extension
migrate = Migrate()

def set_session_variable(key, value):
    """Function to store session variables dynamically."""
    session[key] = value
    
def get_session_variable(key, user_id=None, default=None):
    """Function to retrieve session variables."""
    """Retrieve a session variable (only within request context)."""
    from flask import has_request_context
    if has_request_context():  # Check if a request context exists
        return session.get(key, default)
    return default # Fallback if not in request context

def get_session_config(key, user_id=None, default=None):
    """Function to fetch session configurations from the database, linked to a user if specified."""
    # Delayed import here
    from app.models import SessionConfig #, User  # Assuming User model is defined for user_id  # Assuming you have this model defined
    if user_id:
        config = SessionConfig.query.filter_by(key=key, user_id=user_id).first()
    else:
        config = SessionConfig.query.filter_by(key=key).first()
    if config:
        return config.value
    else:
        return default

def set_session_config(key, value, user_id=None):
    """Function to store session configurations in the database, linked to a user if specified."""
    # Delayed import here
    from app.models import SessionConfig
    existing_config = SessionConfig.query.filter_by(key=key, user_id=user_id).first() if user_id else SessionConfig.query.filter_by(key=key).first()
    if existing_config:
        existing_config.value = value
    else:
        new_config = SessionConfig(key=key, value=value, user_id=user_id)
        db.session.add(new_config)
    db.session.commit()

SESSION_TIMEOUT = 1800  # Set session timeout to 30 minutes (1800 seconds)

def create_app():
    """Factory function to create and configure the Flask app."""
    # Base directory for SQLite or other paths
    basedir = os.path.abspath(os.path.dirname(__file__)) # Get the absolute path to the current directory
    
    # Initialize the Flask app with template folder and configurations
    app = Flask(__name__, template_folder=os.path.join(basedir, 'templates'))
    
    # App configurations
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', f"sqlite:///{os.path.join(basedir, 'railsaathi.db')}")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your_default_secret_key') #dynamic_secret_key  # Use the dynamic SECRET_KEY for CSRF
    
    # Enable CSRF protection
    app.config['WTF_CSRF_ENABLED'] = True  # CSRF protection enabled by default with Flask-WTF
    
    # Initialize extensions with the app instance
    db.init_app(app) # Initialize the database extension
    csrf.init_app(app) # CSRF protection will use the dynamic SECRET_KEY
    migrate.init_app(app, db)  # Initialize Migrate with the app and db
    
    # Session timeout handling and dynamic secret key setup can stay here
    @app.before_request
    def check_session_timeout():
        """Check if the session has timed out."""
        session_last_activity = session.get('last_activity')
        
        if session_last_activity:
            now = time.time()
            if now - session_last_activity > SESSION_TIMEOUT:
                session.clear()  # Clear the session if it has expired
                flash('Your session has expired due to inactivity. Please log in again.', 'warning')
                return redirect(url_for('login.login'))  # Redirect to login page or home if not using login
        
        # Update the session's last activity time
        session['last_activity'] = time.time()
        
        """Load dynamic configurations based on session."""
        """Dynamically manage SECRET_KEY and session variables."""
        if 'SECRET_KEY' not in session:
            # Use database or fallback for SECRET_KEY
            user_id = session.get('user_id', None)
            dynamic_secret_key = get_session_config('SECRET_KEY', user_id=user_id, default=app.config['SECRET_KEY'])
            
            if not dynamic_secret_key:
                # Use fallback SECRET_KEY and store in session and DB
                dynamic_secret_key = app.config['SECRET_KEY']
                set_session_config('SECRET_KEY', dynamic_secret_key, user_id=user_id)

            # Update session with the SECRET_KEY
            session['SECRET_KEY'] = dynamic_secret_key
        
    # Import routes (if needed) or register blueprints here
    # Register blueprints (routes will be modularized in separate files)
    from app.routes import all_blueprints  # Assuming `all_blueprints` is a list of all blueprints 
    # Import blueprints from routes.py
    for blueprint in all_blueprints:
        app.register_blueprint(blueprint)
    
    # Create database tables (for example, during the first setup)
    with app.app_context():
        # Import models to ensure they are registered with SQLAlchemy
        from app import models
        # Optional: Create the database if using Site
        db.create_all() # Create the database schema based on the models
        # Ensure migrations handle schema creation
    
    # Middleware to update session variables during requests
    # Middleware for dynamic session and SECRET_KEY handling
    # @app.before_request
    # def load_dynamic_secret_key():
       
    return app

# You can keep any other imports here if needed, but routes are now in app.pyQL
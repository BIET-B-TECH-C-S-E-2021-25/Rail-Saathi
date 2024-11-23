# Flask app initialization
import os
from flask import Flask, session
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

def create_app():
    """Factory function to create and configure the Flask app."""
    # Base directory for SQLite or other paths
    basedir = os.path.abspath(os.path.dirname(__file__)) # Get the absolute path to the current directory
    
    # Initialize the Flask app with template folder and configurations
    app = Flask(__name__, template_folder=os.path.join(basedir, 'templates'))
    
    # Get user_id from session if available
    # user_id = session.get('user_id', None)

    # Check if SECRET_KEY exists in the session or in the database; if not, set it dynamically
    # dynamic_secret_key = get_session_variable('SECRET_KEY', None)
    # # If no SECRET_KEY in session, try fetching from the database
    # if not dynamic_secret_key:
    #     dynamic_secret_key = get_session_config('SECRET_KEY', user_id=session.get('user_id'), default=None)
         
    # # If SECRET_KEY doesn't exist in the session or DB, use a fallback and store it in the session and DB
    # if not dynamic_secret_key:    
    #     dynamic_secret_key = os.getenv('SECRET_KEY', 'your_default_secret_key')
    #     set_session_variable('SECRET_KEY', dynamic_secret_key)  # Store it in the session
    #     set_session_config('SECRET_KEY', dynamic_secret_key, user_id=session.get('user_id'))  # Store in DB
        
    # App configurations
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', f"sqlite:///{os.path.join(basedir, 'railsaathi.db')}")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your_default_secret_key') #dynamic_secret_key  # Use the dynamic SECRET_KEY for CSRF
    
    # Enable CSRF protection
    app.config['WTF_CSRF_ENABLED'] = True  # CSRF protection enabled by default with Flask-WTF
    
    # Initialize extensions with the app instance
    db.init_app(app)
    csrf.init_app(app) # CSRF protection will use the dynamic SECRET_KEY
    migrate.init_app(app, db)  # Add this line to link the Migrate extension
    
    # Import routes (if needed) or register blueprints here
    # Register blueprints (routes will be modularized in separate files)
    from app.routes import all_blueprints  # Assuming `all_blueprints` is a list of all blueprints 
    # Import blueprints from routes.py
    for blueprint in all_blueprints:
        app.register_blueprint(blueprint)
    
    with app.app_context():
        # Import models to ensure they are registered with SQLAlchemy
        from app import models
        # Optional: Create the database if using Site
        db.create_all()
        # Ensure migrations handle schema creation
        pass
    
    # Middleware to update session variables during requests
    # Middleware for dynamic session and SECRET_KEY handling
    @app.before_request
    def load_dynamic_secret_key():
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
    return app

# You can keep any other imports here if needed, but routes are now in app.pyQL
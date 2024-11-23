import logging
from flask import Blueprint, current_app, flash, render_template, redirect, request, session, url_for
from werkzeug.security import check_password_hash
from app import get_session_config, set_session_config
from app import db
from app.models import User # Import your User model
from sqlalchemy import or_

# Setup logging
logging.basicConfig(level=logging.INFO)

# Define blueprints for different sections
home_bp = Blueprint('home', __name__,template_folder="templates")  # Explicit template folder

@home_bp.route('/',methods=['GET', 'POST'])
def home():
    print("Home route accessed")
    print("Template folder:", home_bp.template_folder)  # Debugging line
    
    if request.method == 'POST':
        # Extract form data
        departure_location = request.form.get('from')
        destination = request.form.get('to')
        travel_date = request.form.get('date')
        travel_class = request.form.get('class')

        # Validate form data
        if not departure_location or not destination or not travel_date or travel_class == 'class':
            flash('Please fill in all fields correctly.', 'danger')
            return redirect(url_for('home.home'))
        
        print(f"Departure Location: {departure_location}")
        print(f"Destination: {destination}")
        print(f"Date: {travel_date}")
        print(f"Class: {travel_class}")
        
        # Handle the form submission logic here (e.g., redirect to search results page)
        return redirect(url_for('search.search', 
                                from_station=departure_location, 
                                to_station=destination, 
                                date=travel_date, 
                                travel_class=travel_class))

    # Render the homepage
    return render_template('index.html',active_page='home.home')

register_bp = Blueprint('register', __name__,template_folder="templates")

@register_bp.route('/register', methods=['GET', 'POST'])
def register():
    # Registration logic
    if request.method == 'POST':
        # Extract form data
        username = request.form.get('username')
        fullname = request.form.get('fullname')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        email = request.form.get('email')
        country_code = request.form.get('country_code')
        mobile = request.form.get('mobile')
        
        # Combine country code and mobile number
        phone = f"{country_code}{mobile}"
        
        # Validate form data
        if not all([username, fullname, password, confirm_password, email, country_code, mobile]):
            flash("All fields are required. Please fill in all details.", "danger")
            return render_template('register.html', active_page='register.register')
        
        if password != confirm_password:
            flash("Passwords do not match. Please try again.", "danger")
            return render_template('register.html', active_page='register.register')

        # Check if username or email already exists in the database
        existing_user = User.query.filter(
            or_(User.username == username)
        ).first()
        if existing_user:
            flash("Username or email already exists. Please choose another.", "danger")
            return redirect(url_for('register.register'))

        # Save the user to the database
        # Create a new user
        try:
            new_user = User(
            username=username,
            fullname=fullname,
            password=password,  # Add hashing if required using Werkzeug # Password will be hashed in the User model
            email=email,
            country_code=country_code,
            phone=phone
            )
            db.session.add(new_user)
            db.session.commit()
            
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for('login.login'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred during registration. Please try again.', 'danger')
            print(f"Error: {e}")  # Log the error for debugging purposes
            return render_template('register.html', active_page='register.register')

    # Render the registration page for GET requests
    return render_template('register.html',active_page='register.register')

search_bp = Blueprint('search', __name__,template_folder="templates")

@search_bp.route('/search', methods=['GET','POST'])
def search():
    try:
        # Train search logic
        # Get query parameters
        from_station = request.args.get('from_station')
        to_station = request.args.get('to_station')
        date = request.args.get('date')
        travel_class = request.args.get('travel_class')

        # Validate query parameters
        if not from_station or not to_station or not date or not travel_class:
            flash("Invalid search parameters. Please try again.", "danger")
            # return redirect(url_for('home.home'))
            return render_template('error.html', message="Invalid search parameters.")
        
        # Fetch search results (mock data here, replace with actual DB query or API call)
        results = [
            {
                "train_name": "Rajdhani Express",
                "train_number": "12345",
                "departure_time": "08:00 AM",
                "arrival_time": "04:00 PM",
                "duration": "8h",
                "available_seats": 50,
                "travel_class": travel_class
            },
            {
                "train_name": "Shatabdi Express",
                "train_number": "54321",
                "departure_time": "09:00 AM",
                "arrival_time": "05:00 PM",
                "duration": "8h",
                "available_seats": 30,
                "travel_class": travel_class
            }
        ]

        # Filter results based on travel class if necessary (mock filtering shown)
        filtered_results = [result for result in results if result['travel_class'] == travel_class]
        
        # Logic for handling the search query, for example, query the database or return results
        # For now, we will just print the values to the console
        print(f"Searching from {from_station} to {to_station} on {date} in class {travel_class}")
    
        # Render the search results page
        return render_template('search.html', 
                               from_station=from_station, 
                               to_station=to_station, 
                               date=date, 
                               travel_class=travel_class, 
                               results=filtered_results,active_page='search.search')
    except Exception as e:
        current_app.logger.error(f"Error in search route: {str(e)}")
        flash("There was an error processing your request. Please try again.", "danger")
        return render_template('error.html', message="Invalid search parameters.")

login_bp = Blueprint('login', __name__,template_folder="templates")

@login_bp.route('/login', methods=['GET', 'POST'], endpoint='login')  # Rename the endpoint to avoid conflicts
def login_route():
    # Login functionality
    if request.method == 'POST':
        # Get form data
        user_input = request.form.get('userInput', '').strip()  # Unified input field
        password = request.form.get('password', '').strip()
        
        # Determine the type of input (username, email, or phone)
        user_id, email, phone = None, None, None
        if "@" in user_input:  # Check for email
            email = user_input
        elif user_input.isdigit():  # Check for phone number
            phone = user_input
        else:  # Assume it's a username
            user_id = user_input
        
         # Validate inputs
        if not (user_input and password):
            flash("Please enter both credentials and password.", "danger")
            return render_template('login.html', active_page='login.login')
        
        # Check if user exists
        try:
            # Build query filters
            query_filters = []
            if user_id:
                query_filters.append(User.username == user_id)
            if email:
                query_filters.append(User.email == email)
            if phone:
                query_filters.append(User.phone.like(f"{phone}%")) # Partial match for phone
            
            if not query_filters:
                flash("Invalid input. Please try again.", "danger")
                return render_template('login.html', active_page='login.login')
            
            # Fetch the user from the database
            user = User.query.filter(or_(*query_filters)).first()
            
            if user:
                # Validate password
                if check_password_hash(user.password, password):
                    session['user_id'] = user.id  # Store user ID in session
                    flash(f"Welcome back, {user.fullname}!", "success")
                    return redirect(url_for('home.home'))  # Redirect to homepage
                else:
                    flash("Incorrect password. Please try again.", "danger")
            else:
                flash("No account found with the provided details.", "danger")

        except Exception as e:
            # Handle unexpected errors
            flash("An error occurred during login. Please try again.", "danger")
            # Log the error (use a logging framework in production)
            logging.error(f"Error during login: {e}")  # Log the error with the logging module
            
        # Render the login page with an error message
        return render_template('login.html', active_page='login.login')
    
    # Render login page for GET request
    return render_template('login.html', active_page='login.login')

forgot_password_bp = Blueprint('forgot_password', __name__,template_folder="templates")

@forgot_password_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    # Forgot password functionality
    if request.method == 'POST':
        # Extract email from the form
        email = request.form.get('email')

        # Validate email
        if not email:
            flash("Please enter your email address.", "danger")
            return render_template('forgot_password.html', active_page='forgot_password.forgot_password')

        # Check if the user exists
        try:
            user = User.query.filter_by(email=email).first()
            if user:
                # Generate a password reset link or token (logic can be implemented later)
                flash("A password reset link has been sent to your email.", "success")
                # Code to send email goes here (e.g., using Flask-Mail or any email library)
            else:
                flash("No account found with that email address.", "danger")
        except Exception as e:
            flash("An error occurred. Please try again.", "danger")
            print(f"Error: {e}")  # Log the error for debugging

        return render_template('forgot_password.html', active_page='forgot_password.forgot_password')

    # Render forgot password page for GET requests
    return render_template('forgot_password.html', active_page='forgot_password.forgot_password')

logout_bp=Blueprint('logout',__name__,template_folder="templates")
@logout_bp.route('/logout')
def logout():
    # Logout logic
    try:
        # Clear the session to log out the user
        session.clear()
        flash("You have been logged out successfully.", "success")
    except Exception as e:
        flash("An error occurred during logout. Please try again.", "danger")
        print(f"Error: {e}")  # Log the error for debugging

    return redirect(url_for('home.home'))

contact_us_bp=Blueprint('contact_us',__name__,template_folder="templates")
@contact_us_bp.route('/contact_us')
def contact_us():
    # Contact us page
    return render_template('contact-us.html', active_page='contact_us.contact_us')

booking_bp=Blueprint('booking',__name__,template_folder="templates")
@booking_bp.route('/booking')
def booking():
    # Booking logic
    return render_template('booking.html', active_page='booking.booking')

history_bp=Blueprint('history',__name__,template_folder="templates")
@history_bp.route('/history')
def history():
    # History page logic
    return render_template('history.html', active_page='history.history')

dashboard_bp=Blueprint('dashboard',__name__,template_folder="templates")
@dashboard_bp.route('/dashboard')
def dashboard():
    # Dashboard logic
    return render_template('dashboard.html', active_page='dashboard.dashboard')

# Consolidate all blueprints into a list
all_blueprints = [
    home_bp,
    register_bp,
    search_bp,
    login_bp,
    forgot_password_bp,
    logout_bp,
    contact_us_bp,
    booking_bp,
    history_bp,
    dashboard_bp,
]

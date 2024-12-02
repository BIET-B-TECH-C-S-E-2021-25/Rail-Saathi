import requests
import openai
import logging
from flask import Blueprint, app, current_app, flash, render_template, redirect, request, session, url_for
from werkzeug.security import check_password_hash
from app import get_session_config, set_session_config
from app import db
from app.models import SessionConfig, Train, User # Import your User model
from sqlalchemy import or_
from functools import wraps

# Setup logging
logging.basicConfig(level=logging.INFO)

# @app.errorhandler(404)
# def page_not_found(e):
#     return render_template('404.html'), 404

# @app.errorhandler(500)
# def internal_server_error(e):
#     return render_template('500.html'), 500

def suggest_trains(user_input, train_list):
    prompt = f"Given these trains {train_list} and user preferences {user_input}, suggest the best options."
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=150
    )
    return response['choices'][0]['text'].strip()

def get_user_by_input(user_input):
    try:
        # Determine input type and build query
        query_filters = []
        if "@" in user_input:  # Email
            query_filters.append(User.email == user_input)
        elif user_input.isdigit():  # Phone
            query_filters.append(User.phone.ilike(f"{user_input}%"))
        else:  # Username
            query_filters.append(User.username == user_input)

        if not query_filters:
            return None

        return User.query.filter(or_(*query_filters)).first()
    except Exception as e:
        current_app.logger.error(f"Error in user validation: {e}")
        return None

def restrict_authenticated(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Check if the user is logged in
        if session.get('user_id') and session.get('is_active'):
            # Redirect to homepage if logged in
            flash("You are already logged in.", "info")
            return redirect(url_for('home.home'))
        return func(*args, **kwargs)
    return wrapper

# Add this function to encapsulate the RapidAPI logic
def fetch_live_station_data(from_station_code, to_station_code, date):
    """Fetch live station data from IRCTC RapidAPI."""
    url = "https://irctc1.p.rapidapi.com/api/v3/trainBetweenStations"
    querystring = {
        "fromStationCode": from_station_code,
        "toStationCode": to_station_code,
        "dateOfJourney": date
        }
    
    headers = {
        "x-rapidapi-key": "5f96361e56msh05fc25d2e8adcdbp12f1d7jsnee997d7bdfcc",
        "x-rapidapi-host": "irctc1.p.rapidapi.com"
        }
    try:
        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()  # Raise an error for bad status codes
        return response.json()
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP Error: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected Error: {e}")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching live station data: {e}")
        return None

# Add this function to encapsulate the RapidAPI logic
def fetch_live_seat_availability_data(class_type,from_station_code,quota,to_station_code, date, train_number):
    """Fetch seat availability data from IRCTC RapidAPI."""
    url = "https://irctc1.p.rapidapi.com/api/v1/checkSeatAvailability"
    querystring = {
        "classType": class_type,
        "fromStationCode": from_station_code,
        "quota":quota,
        "toStationCode": to_station_code,
        "dateOfJourney": date,
        "trainNo":train_number
    }
    headers = {
        "x-rapidapi-key": "5f96361e56msh05fc25d2e8adcdbp12f1d7jsnee997d7bdfcc",  # Replace with your key
        "x-rapidapi-host": "irctc1.p.rapidapi.com"
    }
    try:
        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()  # Raise an error for bad status codes
        return response.json()
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP Error: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected Error: {e}")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching live station data: {e}")
        return None

# Define blueprints for different sections
home_bp = Blueprint('home', __name__,template_folder="templates")  # Explicit template folder

@home_bp.route('/',methods=['GET', 'POST'])
def home():
    print("Home route accessed")
    print("Template folder:", home_bp.template_folder)  # Debugging line
    user_logged_in = 'user_id' in session  # Example check: Replace with your logic
    # Ensure session is active and not expired
    if not session.get('user_id') or not session.get('is_active'):
        session.clear()  # Clear the session if user is not logged in or the session expired
        flash('Your session has expired. Please log in again.', 'warning')
        return redirect(url_for('login.login'))  # Redirect to login page

    # # Existing POST and GET request logic here
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
    return render_template('index.html',user_logged_in=user_logged_in,active_page='home.home')

register_bp = Blueprint('register', __name__,template_folder="templates")

@register_bp.route('/register', methods=['GET', 'POST'])
@restrict_authenticated
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
    user_logged_in = 'user_id' in session  # Example check: Replace with your logic
    try:
        # Train search logic
        # Get query parameters
        from_station = request.args.get('from_station')
        to_station = request.args.get('to_station')
        date = request.args.get('date')
        travel_class = request.args.get('travel_class')

        # Validate query parameters
        if not all([from_station, to_station, date, travel_class]):
            flash("Invalid search parameters. Please try again.", "danger")
            # return redirect(url_for('home.home'))
            return render_template('error.html', message="Invalid search parameters.")
        
        # API integration to fetch train details
        response = fetch_live_station_data(from_station, to_station, date)
        print("API Response:", response)  # Debugging line
        
        # Handle if the response is None or empty
        if response is None or 'data' not in response or not response['data']:
            flash("Unable to fetch train data. Please try again.", "danger")
            return render_template('error.html', message="Error fetching train data.")
        
       # Process the response and display train data
        train_data = response['data']
        if not train_data:
            flash("No trains found for the given search criteria.", "warning")
            return render_template('error.html', message="No trains found.")
        
        #cond for seat availability according to class_type and travelling_class
        l=len(train_data)
        for i in range(l):
            for train in train_data:
                if train[i]['class_type']==travel_class:
                    #seat availability logic by fetching data with new api and new fetch func
                    response2=fetch_live_seat_availability_data(train[i][class_type],from_station_code,quota,to_station_code, date, train_number)
                    total_fare_and_seat=
                    pass

        # Render the search results page
        return render_template('search.html', 
                               results=train_data,
                               from_station=from_station, 
                               to_station=to_station, 
                               date=date, 
                               travel_class=travel_class,
                               user_logged_in=user_logged_in,
                               active_page='search.search')
    except Exception as e:
        current_app.logger.error(f"Error in search route: {str(e)}")
        flash("There was an error processing your request. Please try again.", "danger")
        return render_template('error.html', message="An error occurred.")

login_bp = Blueprint('login', __name__,template_folder="templates")

@login_bp.route('/login', methods=['GET', 'POST'], endpoint='login')  # Rename the endpoint to avoid conflicts
@restrict_authenticated
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
            flash("Please enter both credentials and password.", "warning")
            return render_template('login.html', active_page='login.login')
        
        # Check if user exists
        try:
            user = get_user_by_input(user_input)
            if user:
                # Validate password
                if check_password_hash(user.password, password):
                    session['user_id'] = user.id  # Store user ID in session
                    session['is_active'] = True  # Mark user as active in the session
                    user.is_active = True  # Update the database
                    db.session.commit()
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
        user_id = session.get('user_id')
        if user_id:
            # Update user to inactive
            user = User.query.get(user_id)
            if user:
                user.is_active = False
                db.session.commit()
        
        # Clear the session to log out the user
        session.clear()
        flash("You have been logged out successfully.", "success")
        # return redirect(url_for('login.login'))
    
    except Exception as e:
        flash("An error occurred during logout. Please try again.", "danger")
        print(f"Error: {e}")  # Log the error for debugging

    return redirect(url_for('home.home'))

contact_us_bp=Blueprint('contact_us',__name__,template_folder="templates")
@contact_us_bp.route('/contact_us')
def contact_us():
    # Contact us page
    user_logged_in = 'user_id' in session  # Example check: Replace with your logic
    return render_template('contact-us.html', user_logged_in=user_logged_in, active_page='contact_us.contact_us')

booking_bp=Blueprint('booking',__name__,template_folder="templates")
@booking_bp.route('/booking')
def booking():
    # Booking logic
    train_number = request.args.get('train_number')
    date = request.args.get('date')
    if not train_number or not date:
        flash("Invalid booking parameters. Please try again.", "danger")
        return redirect(url_for('search.search'))
    return render_template('booking.html', train_number=train_number, active_page='booking.booking')

history_bp=Blueprint('history',__name__,template_folder="templates")
@history_bp.route('/history')
def history():
    # History page logic
    return render_template('history.html', active_page='history.history')

dashboard_bp=Blueprint('dashboard',__name__,template_folder="templates")
@dashboard_bp.route('/dashboard', methods=['GET'])
def dashboard():
    # Dashboard logic
    # Check if the user is logged in
    if 'user_id' not in session:
        return redirect(url_for('login.login'))  # Redirect to login if not logged in
    
    user_logged_in = 'user_id' in session  # Example check: Replace with your logic
    # Retrieve the logged-in user's details
    user_id = session['user_id']
    user = User.query.get(user_id)
    if not user:
        return redirect(url_for('login.login'))  # Redirect if user doesn't exist
    
    # Fetch user-specific session configurations and available trains
    session_configs = SessionConfig.query.filter_by(user_id=user_id).all()
    available_trains = Train.query.all()
    
    # Render the dashboard with user-specific data
    return render_template('dashboard.html',user=user, configs=session_configs, trains=available_trains, user_logged_in=user_logged_in,active_page='dashboard.dashboard')

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

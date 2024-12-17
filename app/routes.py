import time
from datetime import datetime
import requests
import openai
import logging
import os
from flask import Blueprint, app, current_app, flash, render_template, redirect, request, session, url_for
from werkzeug.security import check_password_hash
from app import get_session_config, set_session_config
from app import db
from app.models import SessionConfig, Train, User, Booking # Import your Booking model
from sqlalchemy import or_
from functools import wraps

# Setup logging
logging.basicConfig(level=logging.INFO)

# def suggest_trains(user_input, train_list):
#     prompt = f"Given these trains {train_list} and user preferences {user_input}, suggest the best options."
#     response = openai.Completion.create(
#         engine="text-davinci-003",
#         prompt=prompt,
#         max_tokens=150
#     )
#     return response['choices'][0]['text'].strip()

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
    def decorated_function(*args, **kwargs):
        if 'user_id' in session:
            return redirect(url_for('dashboard.dashboard'))
        return func(*args, **kwargs)
    return decorated_function

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
        "x-rapidapi-key": os.getenv("RAPIDAPI_KEY"),
        "x-rapidapi-host": "irctc1.p.rapidapi.com"
    }
    try:
        # response = fetch_data_with_backoff(url, headers, params=querystring, retries=5)
        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()  # Raise an error for bad status codes
        return response.json()
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP Error: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected Error: {e}")
        return None

def fetch_live_seat_availability_data(class_type, from_station_code, quota, to_station_code, train_number, date):
    """Fetch seat availability data from IRCTC RapidAPI."""
    url = "https://irctc1.p.rapidapi.com/api/v1/checkSeatAvailability"
    querystring = {
        "classType": class_type,
        "fromStationCode": from_station_code,
        "quota": quota,
        "toStationCode": to_station_code,
        "trainNo": train_number,
        "date": date
    }
    
    headers = {
        "x-rapidapi-key": os.getenv("RAPIDAPI_KEY"),  # Replace with your key
        "x-rapidapi-host": "irctc1.p.rapidapi.com"
    }
    
    try:
        # response = fetch_data_with_backoff(url, headers, params=querystring, retries=5)
        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()  # Raise an error for bad status codes
        return response.json()
    except requests.exceptions.HTTPError as e:
        current_app.logger.error(f"HTTP Error: {e}")
        return None
    except Exception as e:
        current_app.logger.error(f"Unexpected Error: {e}")
        return None

# Define blueprints for different sections
home_bp = Blueprint('home', __name__, template_folder="templates")  # Explicit template folder
@home_bp.route('/', methods=['GET', 'POST'])
def home():
    print("Home route accessed")
    print("Template folder:", home_bp.template_folder)  # Debugging line
    user_logged_in = 'user_id' in session  # Example check: Replace with your logic
    # Ensure session is active and not expired
    if not session.get('user_id') or not session.get('is_active'):
        session.clear()  # Clear the session if user is not logged in or the session expired
        flash('Your session has expired. Please log in again.', 'warning')
        return redirect(url_for('login.login'))  # Redirect to login page

    # Existing POST and GET request logic here
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
            flash('An error occurred during registration. Please try again.', "danger")
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
        
        print(f"From: {from_station}, To: {to_station}, Date: {date}, Class: {travel_class}")
        # Validate query parameters
        if not all([from_station, to_station, date, travel_class]):
            flash("Invalid search parameters. Please try again.", "danger")
            return render_template('error.html', message="Invalid search parameters.")
        
        # API integration to fetch train details
        response = fetch_live_station_data(from_station, to_station, date)
        
        # Handle if the response is None or empty
        if response is None or 'data' not in response or not response['data']:
            flash("Unable to fetch train data. Please try again.", "danger")
            return render_template('error.html', message="Error fetching train data.")
        
        # Process the response and display train data
        train_data = response['data']
        if not train_data:
            flash("No trains found for the given search criteria.", "warning")
            return render_template('error.html', message="No trains found.")
        
        train_i=[]
        for train_d in train_data:
            for class_type in train_d['class_type']:
                if class_type == travel_class:
                    train_i.append(train_d)
        train_data=train_i
        
        date_str = date
        # Parse the date string
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        # Reformat the date
        formatted_date = date_obj.strftime("%d-%m-%Y")
        
        # print(formatted_date,"\n")  # Output: 19-12-2024 #for debugging
        
        # Fetch seat availability data
        available_seats = []
        for train in train_data:
            for class_type in train['class_type']:
                if class_type == travel_class:
                    # print(train['train_name'],train['class_type'],train['train_number'], "\n") #for debugging
                    # Fetch seat availability for the train
                    response = fetch_live_seat_availability_data(
                        travel_class,
                        from_station,
                        "GN",
                        to_station,
                        train["train_number"],
                        formatted_date
                    )    
                    if response and 'data' in response:
                        # Append the seat availability data to the list
                        s=response['data']
                        # print("\n",s) # for debugging
                        available_seats.append({'train_number':train['train_number'], 'as':s[0]['current_status']})
                        # print("\n",{'train_number':train['train_number'], 'as':s[0]['current_status']}) #for debugging
        # print("\n",available_seats,"\n") #for debugging
                
        # Suggest trains based on user preferences
        # user_input = f"From {from_station} to {to_station} on {date} in {travel_class} class"
        # suggested_trains = suggest_trains(user_input, [train['train_name'] for train in train_data])
        # print("Suggested trains:", suggested_trains)
        
        
        # Render the search results page with the fetched data
        return render_template('search.html',
                               results=train_data,
                               available_seats=available_seats,
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

logout_bp = Blueprint('logout', __name__, template_folder="templates")
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
    
    except Exception as e:
        flash("An error occurred during logout. Please try again.", "danger")
        print(f"Error: {e}")  # Log the error for debugging

    return redirect(url_for('home.home'))

contact_us_bp = Blueprint('contact_us', __name__, template_folder="templates")
@contact_us_bp.route('/contact_us', methods=['GET', 'POST'])
def contact_us():
    # Contact us page
    user_logged_in = 'user_id' in session  # Example check: Replace with your logic

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')

        if not name or not email or not message:
            flash('Please fill in all fields.', 'danger')
            return render_template('contact-us.html', user_logged_in=user_logged_in, active_page='contact_us.contact_us')
        
        # Process the form data here (e.g., send email or save to database)
        flash('Your message has been sent successfully!', 'success')
        # Redirect to the contact us page
        return redirect(url_for('contact_us.contact_us'))

    return render_template('contact-us.html', user_logged_in=user_logged_in, active_page='contact_us.contact_us')

booking_bp = Blueprint('booking', __name__, template_folder="templates")

@booking_bp.route('/booking', methods=['GET', 'POST'])
def booking():
    user_logged_in = 'user_id' in session

    if not user_logged_in:
        flash("You need to be logged in to proceed with booking.", "warning")
        return redirect(url_for('login.login'))
    
    if request.method == 'POST':
        # Handle form submission
        train_number = request.form.get('train_number')
        date = request.form.get('date')
        from_station = request.form.get('from_station')
        to_station = request.form.get('to_station')
        travel_class = request.form.get('travel_class')
    else:
        # Handle GET request
        train_number = request.args.get('train_number')
        date = request.args.get('date')
        from_station = request.args.get('from_station')
        to_station = request.args.get('to_station')
        travel_class = request.args.get('travel_class')

    print(f"Train Number: {train_number}, Date: {date}, From: {from_station}, To: {to_station}, Class: {travel_class}")
        
    if not all([train_number, date, from_station, to_station, travel_class]):
        flash("Invalid booking parameters. Please try again.", "danger")
        return redirect(url_for('search.search'))

    # Fetch train details
    train_info_response = fetch_live_station_data(from_station, to_station, date)
    if not train_info_response:
        flash("Train details not found.", "danger")
        return redirect(url_for('search.search'))

    train_info_list = train_info_response['data']
    train_info = next((train for train in train_info_list if train['train_number'] == train_number), None)
    if not train_info:
        flash("Train not found.", "danger")
        return redirect(url_for('search.search'))

    # Fetch seat availability
    seat_availability_response = fetch_live_seat_availability_data(
        travel_class,
        from_station,
        "GN",
        to_station,
        train_number,
        date
    )
    if not seat_availability_response:
        flash("Seat availability information not found.", "danger")
        return redirect(url_for('search.search'))

    seat_availability = seat_availability_response['data']
    
    return render_template('booking.html',
                            train_info=train_info,
                            seat_availability=seat_availability,
                            date=date,
                            travel_class=travel_class,
                            user_logged_in=user_logged_in,
                            active_page='booking.booking')

@booking_bp.route('/confirm_booking', methods=['POST'])
def confirm_booking():
    # Retrieve form data
    train_number = request.form.get('train_number')
    date_str = request.form.get('date')
    from_station = request.form.get('from_station')
    to_station = request.form.get('to_station')
    travel_class = request.form.get('travel_class')
    passenger_name = request.form.get('passenger_name')
    passenger_age = request.form.get('passenger_age')
    passenger_gender = request.form.get('passenger_gender')
    payment_method = request.form.get('payment_method')
    
    # Convert 'date_str' to a Python date object
    if date_str:
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash("Invalid date format. Please try again.", "danger")
            return redirect(url_for('booking.booking'))
    else:
        flash("Invalid date. Please try again.", "danger")
        return redirect(url_for('booking.booking'))
    
    # Check if the user is logged in and active
    user_id = session.get('user_id')
    if user_id:
        user = User.query.get(user_id)
        if not user or not user.is_active:
            session.clear()
            flash("Your session has expired or user does not exist. Please log in.", "warning")
            return redirect(url_for('login.login'))
    else:
        flash("You need to be logged in to make a booking.", "danger")
        return redirect(url_for('login.login'))
    
    # Ensure the train exists
    # train = Train.query.filter_by(train_number=train_number).first()
    # if not train:
    #     flash("Train not found. Please select a valid train.", "danger")
    #     return redirect(url_for('booking.booking'))

    # Validate passenger age
    try:
        passenger_age = int(passenger_age)
    except ValueError:
        flash("Invalid passenger age. Please enter a valid number.", "danger")
        return redirect(url_for('booking.booking'))

    # Process payment (mock implementation)
    payment_success = True  # Assume payment is successful

    if payment_success:
        # Save booking details to the database
        booking = Booking(
            user_id=user_id,
            # train_number=train.train_number,
            date=date,
            from_station=from_station,
            to_station=to_station,
            travel_class=travel_class,
            passenger_name=passenger_name,
            passenger_age=passenger_age,
            passenger_gender=passenger_gender,
            payment_method=payment_method
        )
        db.session.add(booking)
        db.session.commit()

        flash("Booking confirmed! Your ticket has been booked.", "success")
        return render_template('payment.html', booking_id=booking.id)
    else:
        flash("Payment failed. Please try again.", "danger")
        return redirect(url_for('booking.booking'))

# @booking_bp.route('/payment_success', methods=['POST'])
# def payment_success():
#     payment_id = request.form.get('razorpay_payment_id')
#     order_id = request.form.get('razorpay_order_id')
#     signature = request.form.get('razorpay_signature')
#     # Verify the payment signature
#     params_dict = {
#         'razorpay_order_id': order_id,
#         'razorpay_payment_id': payment_id,
#         'razorpay_signature': signature
#     }
#     try:
#         razorpay_client.utility.verify_payment_signature(params_dict)
#         # Payment is successful and verified
#         flash("Payment successful!", "success")
#         # Save booking details to the database
#         return redirect(url_for('dashboard.dashboard'))
#     except razorpay.errors.SignatureVerificationError:
#         flash("Payment verification failed. Please try again.", "danger")
#         return redirect(url_for('booking.booking'))

history_bp = Blueprint('history', __name__, template_folder="templates")
@history_bp.route('/history')
def history():
    # History page logic
    return render_template('history.html', active_page='history.history')

dashboard_bp = Blueprint('dashboard', __name__, template_folder="templates")

@dashboard_bp.route('/dashboard', methods=['GET'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login.login'))
    
    user_logged_in = 'user_id' in session
    user_id = session['user_id']
    user = User.query.get(user_id)
    if not user:
        return redirect(url_for('login.login'))
    
    session_configs = SessionConfig.query.filter_by(user_id=user_id).all()
    # available_trains = Train.query.all()
    # Fetch seat availability for each train
    # seat_availability = []
    # for train in available_trains:
    #     seat_response = fetch_live_seat_availability_data(
    #         travel_class=travel_class,  # Example class type
    #         from_station_code=train.source_code,  # Assuming source_code attribute
    #         quota='GN',
    #         to_station_code=train.destination_code,  # Assuming destination_code attribute
    #         train_number=train.train_number,
    #         date=datetime.today().strftime('%Y-%m-%d')  # Example date
    #     )
    #     if seat_response and 'data' in seat_response:
    #         seat_availability.append(seat_response['data'])
    #     else:
    #         seat_availability.append({'seats_available': 'N/A'})
    # Fetch user bookings
    bookings = Booking.query.filter_by(user_id=user_id).all()

    # Check if a specific booking_id is provided
    booking_id = request.args.get('booking_id')
    latest_booking = None
    if booking_id:
        latest_booking = Booking.query.get(booking_id)

    return render_template('dashboard.html',
                           user=user,
                           configs=session_configs,
                        #    trains=available_trains,
                        #    seat_availability=seat_availability,
                           bookings=bookings,
                           latest_booking=latest_booking,
                           user_logged_in=user_logged_in,
                           active_page='dashboard.dashboard')

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

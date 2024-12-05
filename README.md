# RailSaathi - AI-Powered Railway Assistance System

## Project Overview

**RailSaathi** is an AI-powered railway assistance system that simplifies ticket booking for the Indian Railways. It features user authentication, train search, real-time seat booking, and AI-driven suggestions. Built with Flask, SQLite, and JavaScript, this project aims to enhance user experience and streamline railway operations. Deployable on Render.

---

## Features

- **User Authentication**: Secure login and registration processes.
- **Train Search Functionality**: Search for trains between specified source and destination stations.
- **Seat Booking**: Real-time seat booking with immediate confirmation.
- **AI-Powered Suggestions**: Intelligent recommendations for seat selection.
- **User Dashboard**: Manage bookings and view travel history.
- **Responsive Design**: Mobile-friendly interface for all devices.

---

## Technologies Used

- **Backend**: Flask (Python)
- **Database**: SQLite with SQLAlchemy ORM
- **Frontend**: HTML, CSS, JavaScript
- **AI Model**: Machine learning algorithms for seat suggestions
- **Deployment**: Render

---

## Setup and Installation

### Prerequisites

- Python 3.13.0 installed
- SQLite3 installed
- Git installed

### Steps to Run Locally

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/RailSaathi.git
   ```

2. **Change into the project directory**:
   ```bash
   cd RailSaathi
   ```

3. **Create a virtual environment and activate it**:
   ```bash
   python3 -m venv venv
   ```
   - **On Windows**:
     ```bash
     venv\Scripts\activate
     ```
   - **On macOS/Linux**:
     ```bash
     source venv/bin/activate
     ```

4. **Install the required dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Set up the database**:
   - Import the provided SQL script to set up the database:
     ```sql
     railsaathi.sql
     ```
   - Update the `.env` file with your SQLite credentials:
     ```plaintext
     DB_URI=sqlite:///railsathi.db
     ```

6. **Run the application**:
   ```bash
   python app.py
   ```

7. **Access the application**:
   Open your browser and visit:
   ```plaintext
   http://127.0.0.1:5000
   ```

---

## Deployment

### Render

1. Add a `.env` file with your environment variables:
   ```plaintext
   DB_URI=sqlite:///railsathi.db
   DATABASE_URL=sqlite:///railsaathi.db
   SECRET_KEY=your_secret_key
   FLASK_APP=app.app
   ```
2. Update the `render.yaml` with necessary deployment configurations.
3. Push the changes to your repository and link it with Render.

---

## Environment Variables

- Make sure `.env` is added to `.gitignore` for security.
- Required variables:
  - `DB_URI`: SQLite database connection string.
  - `DATABASE_URL`: SQLite database connection string.
  - `SECRET_KEY`: Your secret key for Flask application.
  - `FLASK_APP`: Entry point of your Flask application.

---

## File Structure Overview

- **`app/`**: Contains all Python scripts and core logic.
  - `ai_logic.py`: AI recommendation system logic.
  - `auth.py`: User authentication.
  - `bookings.py`: Booking management.
  - `forms.py`: Web forms.
  - `models.py`: Database models.
  - `trains.py`: Train search and management.
- **`static/`**: Static assets like CSS, JavaScript, and images.
- **`templates/`**: HTML templates for rendering pages.
- **`migrations/`**: Alembic migration files for database changes.

---

## Future Work

- Real-time train updates and notifications.
- Expand the AI model for personalized recommendations.
- Add multi-language support.
- Integrate third-party APIs for food ordering and other services.

---

## Team Members

- **Ayush Goel** - Backend, Database Integration, AI Logic, Deployment
- **Meghna Singh** - Frontend UI/UX, CSS Design, Template Structure
- **Rajeev Mishra** - Frontend JavaScript & Dynamic Features
- **Azad Tiwari** - User Dashboard, Interactive Components

---

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any suggestions or improvements.

---

## License

This project is licensed under the MIT License - see the LICENSE file for details.
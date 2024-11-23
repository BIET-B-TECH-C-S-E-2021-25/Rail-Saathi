from waitress import serve
from app import create_app
from flask_migrate import Migrate
from app import db  # Make sure db is imported here

# Create the app instance using the factory function
app = create_app()

# Initialize Flask-Migrate with the app and db
migrate = Migrate(app, db)

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8000))  # Default to 8000 if PORT is not set
    serve(app, host="0.0.0.0", port=port) # Using waitress to serve the app
    # app.run(debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true')
    # app.run(debug=True)

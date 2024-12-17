import os
from waitress import serve
# from flask_script import Manager
from flask_migrate import Migrate #, MigrateCommand
from app import create_app,db  # Make sure db is imported here

# Create the app instance using the factory function
app = create_app()

# Initialize Flask-Migrate with the app and db
migrate = Migrate(app, db)

# Initialize Flask-Script Manager
# manager = Manager(app)
# manager.add_command('db', MigrateCommand)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))  # Default to 8000 if PORT is not set
    serve(app, host="0.0.0.0", port=port)  # Using waitress to serve the app
    
    # Check if the script is run with the 'runserver' command
    # if 'runserver' in os.sys.argv:
    #     serve(app, host="0.0.0.0", port=port)  # Using waitress to serve the app
    # else:
    #     manager.run()
    # app.run(host=' ', port=port)  # Run the app
    # app.run(debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true')
    # app.run(debug=True)

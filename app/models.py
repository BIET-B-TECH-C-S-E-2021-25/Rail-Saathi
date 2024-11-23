# SQLAlchemy models
from app import db
from werkzeug.security import generate_password_hash

class User(db.Model):
    # __tablename__ = "users"  # Explicitly define table name
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    fullname = db.Column(db.String(120), nullable=False)
    password = db.Column(db.String(200), nullable=False)  # Store hashed passwords
    email=db.Column(db.String(120),unique=True,nullable=False,index=True)
    country_code = db.Column(db.String(10), nullable=False)
    phone=db.Column(db.String(15),unique=True,nullable=False, index=True)
    # Add a new column
    is_active = db.Column(db.Boolean, default=True)
    session_configs = db.relationship('SessionConfig', back_populates='user', cascade="all, delete-orphan")  # Relationship to SessionConfig
    
    __table_args__ = (
        db.UniqueConstraint('email', name='uq_user_email'),
        db.UniqueConstraint('phone', name='uq_user_phone'),
    )
    
    def __init__(self, username,fullname, password, email, country_code, phone):
        self.username = username
        self.fullname=fullname
        self.email = email
        self.country_code=country_code
        self.phone = phone
        self.password = generate_password_hash(password) # Hash the password
    
    def __repr__(self):
        return f"<User {self.username}, Email: {self.email}>"

# Train Model
class Train(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    train_number = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    source = db.Column(db.String(100), nullable=False)
    destination = db.Column(db.String(100), nullable=False)
    timings = db.Column(db.String(100), nullable=True)
    seats_available = db.Column(db.Integer, nullable=False)
        
    def __repr__(self):
        return f"<Train {self.name}, Seats Available: {self.seats_available}>"

# SessionConfig Model
class SessionConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(128), unique=True, nullable=False,index=True)
    value = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Nullable for global configs
    
    user = db.relationship('User', back_populates='session_configs')  # Bidirectional relationship with User model
    
    __table_args__ = (
        db.Index('ix_sessionconfig_key', 'key'),  # Index for faster lookups
    )
    
    def __repr__(self):
        return f"<SessionConfig {self.key}={self.value}>"

# Create the table (or run migrations to create it)
# db.create_all()
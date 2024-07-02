from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
import re;

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///garden.db'  # Path to the SQLite database file
db = SQLAlchemy(app)

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)
    flowers = db.relationship('Flower', backref='user', lazy=True)

# Flower model
class Flower(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    grid_position = db.Column(db.Integer, nullable=True)  # New field for grid position

# Function to validate password complexity
def validate_password(password):
    # Password must be at least 8 characters long and contain at least one digit
    if len(password) < 8 or not re.search(r'\d', password):
        return False
    return True

# Create tables if they do not exist
@app.before_request
def create_tables():
    if not hasattr(create_tables, 'has_run'):
        db.create_all()
        create_tables.has_run = True

# Index route
@app.route('/')
def index():
    error_message = session.pop('error_message', None)
    return render_template('index.html', error_message=error_message)

# Register route
@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    password = request.form['password']
    
    # Check if username already exists
    if User.query.filter_by(username=username).first():
        session['error_message'] = "Username already exists!"
        return redirect(url_for('index'))
    
    # Validate password 
    if not validate_password(password):
        session['error_message'] = "Password must be at least 8 characters long and contain at least one digit."
        return redirect(url_for('index'))

    # Add user to database
    new_user = User(username=username, password=password)
    db.session.add(new_user)
    db.session.commit()
    session['username'] = username
    return redirect(url_for('home'))

# Login route
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    user = User.query.filter_by(username=username).first()
    if not user:
        session['error_message'] = "User does not exist!"
    elif user.password != password:
        session['error_message'] = "Wrong password!"
    else:
        session['username'] = username
        return redirect(url_for('home'))
    return redirect(url_for('index'))

# Logout route
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

# Home route
@app.route('/home')
def home():
    if 'username' not in session:
        return redirect(url_for('index'))
    username = session['username']
    user = User.query.filter_by(username=username).first()
    user_flowers = user.flowers
    return render_template('home.html', username=username, user_flowers=user_flowers)

# Plant flower route
@app.route('/plant_flower/<flower_id>')
def plant_flower(flower_id):
    if 'username' not in session:
        return redirect(url_for('index'))
    username = session['username']
    user = User.query.filter_by(username=username).first()
    
    # Check if the user has already chosen a flower
    if Flower.query.filter_by(user_id=user.id).count() > 0:
        flash("You have already chosen a flower.", "error")
        return redirect(url_for('home'))
    
    new_flower = Flower(name=f'Flower {flower_id}', user=user)
    db.session.add(new_flower)
    db.session.commit()
    
    return redirect(url_for('home'))

# Garden route
@app.route('/garden')
def garden():
    if 'username' not in session:
        return redirect(url_for('index'))

    username = session['username']
    user = User.query.filter_by(username=username).first()
    user_flower = Flower.query.filter_by(user_id=user.id).first()

    # Ensure the user has chosen a flower
    if not user_flower:
        flash("You need to choose a flower first.", "error")
        return redirect(url_for('home'))

    # Get assigned positions
    assigned_positions = {flower.grid_position: flower for flower in Flower.query.all() if flower.grid_position is not None}
    user_assigned_position = user_flower.grid_position if user_flower.grid_position is not None else None

    return render_template('garden.html', assigned_positions=assigned_positions, user_assigned_position=user_assigned_position, user_flower=user_flower)



# Plant flower in grid route
@app.route('/plant_flower_in_grid/<int:position>')
def plant_flower_in_grid(position):
    if 'username' not in session:
        return redirect(url_for('index'))
    
    username = session['username']
    user = User.query.filter_by(username=username).first()
    
    # Ensure the user has chosen a flower
    user_flower = Flower.query.filter_by(user_id=user.id).first()
    if not user_flower:
        flash("You need to choose a flower first.", "error")
        return redirect(url_for('home'))
    
    # Check if the position is already occupied
    if Flower.query.filter_by(grid_position=position).count() > 0:
        flash("This position is already occupied.", "error")
        return redirect(url_for('garden'))
    
    # Plant the flower in the grid
    user_flower.grid_position = position
    db.session.commit()
    
    return redirect(url_for('garden'))

@app.route('/assign_field/<int:position>', methods=['POST'])
def assign_field(position):
    if 'username' not in session:
        return redirect(url_for('index'))

    username = session['username']
    user = User.query.filter_by(username=username).first()
    user_flower = Flower.query.filter_by(user_id=user.id).first()

    if not user_flower:
        flash("You need to choose a flower first.", "error")
        return redirect(url_for('home'))

    # Check if the position is already occupied
    existing_flower = Flower.query.filter_by(grid_position=position).first()
    if existing_flower:
        flash(f"{existing_flower.user.username} already planted something here!", "error")
        return redirect(url_for('garden'))

    # Assign the grid position to the user's flower
    user_flower.grid_position = position
    db.session.commit()

    return redirect(url_for('garden'))



if __name__ == '__main__':
    app.run(debug=True)

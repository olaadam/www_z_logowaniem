from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import pytz

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
    grid_position = db.Column(db.Integer, nullable=True)
    planting_time = db.Column(db.DateTime, nullable=True)
    last_watering_time = db.Column(db.DateTime, nullable=True)  # Nowe pole
    previous_watering_time = db.Column(db.DateTime, nullable=True)  # Nowe pole


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
    if User.query.filter_by(username=username).first():
        session['error_message'] = "Username already exists!"
    else:
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        session['username'] = username
        return redirect(url_for('home'))
    return redirect(url_for('index'))

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
    user_flower.planting_time = datetime.now()  # Record planting time
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
    user_flower.planting_time = datetime.now()  # Record planting time
    db.session.commit()

    return redirect(url_for('garden'))

@app.route('/water_plant', methods=['POST'])
def water_plant():
    if 'username' not in session:
        return redirect(url_for('index'))

    username = session['username']
    user = User.query.filter_by(username=username).first()
    user_flower = Flower.query.filter_by(user_id=user.id).first()

    if not user_flower or user_flower.grid_position is None:
        return jsonify({'success': False, 'message': 'No plant found to water!'})

    current_time = datetime.now()
    planting_time = user_flower.planting_time
    time_diff = (current_time - planting_time).total_seconds()

    if time_diff <= 24 * 3600:
        user_flower.previous_watering_time = user_flower.last_watering_time
        user_flower.last_watering_time = current_time
        db.session.commit()
        
        # Convert last_watering_time and previous_watering_time to Warsaw time zone
        warsaw = pytz.timezone('Europe/Warsaw')
        last_watering_time_warsaw = user_flower.last_watering_time.astimezone(warsaw)
        previous_watering_time_warsaw = user_flower.previous_watering_time.astimezone(warsaw) if user_flower.previous_watering_time else None

        return jsonify({
            'success': True,
            'last_watering_time': last_watering_time_warsaw.strftime("%Y-%m-%d %H:%M:%S") if last_watering_time_warsaw else None,
            'previous_watering_time': previous_watering_time_warsaw.strftime("%Y-%m-%d %H:%M:%S") if previous_watering_time_warsaw else None,
            'planting_time': planting_time.strftime("%Y-%m-%d %H:%M:%S")
        })
    else:
        db.session.delete(user_flower)
        db.session.commit()
        return jsonify({'success': False, 'message': 'You took too long to water the plant!'})


@app.route('/get_plant_dates', methods=['GET'])
def get_plant_dates():
    if 'username' not in session:
        return redirect(url_for('index'))

    username = session['username']
    user = User.query.filter_by(username=username).first()
    user_flower = Flower.query.filter_by(user_id=user.id).first()

    if not user_flower:
        return jsonify({'plant_dates': {}})

    return jsonify({
        'plant_dates': {
            'last_watering': user_flower.last_watering_time,
            'previous_watering': user_flower.previous_watering_time,
            'planting_date': user_flower.planting_time
        }
    })

# Delete account route
@app.route('/delete_account')
def delete_account():
    if 'username' in session:
        username = session['username']
        user = User.query.filter_by(username=username).first()
        if user:
            # Delete user's flowers first
            Flower.query.filter_by(user_id=user.id).delete()
            # Delete user account
            db.session.delete(user)
            db.session.commit()
        session.pop('username', None)
        return redirect(url_for('index'))
    else:
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)

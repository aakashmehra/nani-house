# Authentication routes and logic for Battle Lanes

from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from models import db, User, Player
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

@auth_bp.route('/launch')
def launch():
    """Launch page - first page users see"""
    return render_template('auth_launch.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and authentication - accepts username or email"""
    if request.method == 'POST':
        username_or_email = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username_or_email or not password:
            return render_template('login.html', error='Username and password are required')
        
        # Check if input is an email (contains @) or username
        if '@' in username_or_email:
            # Search by email
            user = User.query.filter_by(email=username_or_email).first()
        else:
            # Search by username
            user = User.query.filter_by(username=username_or_email).first()
        
        if user and user.check_password(password):
            # Login successful
            session['user_id'] = user.id
            session['username'] = user.username
            # Clear is_guest flag if it was set from previous guest session
            session.pop('is_guest', None)
            
            # Ensure player record exists with 100 coins
            player = Player.query.filter_by(user_id=user.id).first()
            if not player:
                # Create player record with 100 coins
                player = Player(
                    user_id=user.id,
                    coins=100,
                    wins=0,
                    losses=0,
                    total_games=0
                )
                db.session.add(player)
            elif player.coins < 100:
                # If player exists but has less than 100 coins, set to 100
                player.coins = 100
            
            # Update last login
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            return redirect(url_for('main'))
        else:
            return render_template('login.html', error='Invalid username or password')
    
    return render_template('login.html')

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    """Create account page and registration"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        if not username or not email or not password:
            return render_template('signup.html', error='All fields are required')
        
        if password != confirm_password:
            return render_template('signup.html', error='Passwords do not match')
        
        if len(password) < 6:
            return render_template('signup.html', error='Password must be at least 6 characters')
        
        # Check if username or email already exists
        if User.query.filter_by(username=username).first():
            return render_template('signup.html', error='Username already exists')
        
        if User.query.filter_by(email=email).first():
            return render_template('signup.html', error='Email already registered')
        
        try:
            # Create new user with hashed password
            new_user = User(
                username=username,
                email=email,
                is_active=True,
                is_verified=False
            )
            new_user.set_password(password)  # This hashes the password
            
            db.session.add(new_user)
            db.session.flush()  # Get the user ID
            
            # Create associated player profile with 100 coins
            new_player = Player(
                user_id=new_user.id,
                coins=100,  # Starting coins
                wins=0,
                losses=0,
                total_games=0
            )
            db.session.add(new_player)
            
            db.session.commit()
            
            # Auto-login after signup
            session['user_id'] = new_user.id
            session['username'] = new_user.username
            # Clear is_guest flag if it was set from previous guest session
            session.pop('is_guest', None)
            
            return redirect(url_for('main'))
            
        except Exception as e:
            db.session.rollback()
            return render_template('signup.html', error=f'Error creating account: {str(e)}')
    
    return render_template('signup.html')

@auth_bp.route('/check_username')
def check_username():
    """API endpoint to check if username exists"""
    username = request.args.get('username', '').strip()
    current_user_id = session.get('user_id')
    
    if not username:
        return jsonify({'available': False, 'message': 'Username is required'})
    
    existing_user = User.query.filter_by(username=username).first()
    
    # If editing own profile, allow current username
    if existing_user and existing_user.id == current_user_id:
        return jsonify({'available': True, 'message': 'Username available'})
    
    if existing_user:
        return jsonify({'available': False, 'message': 'Username already exists'})
    
    return jsonify({'available': True, 'message': 'Username available'})

@auth_bp.route('/guest_play')
def guest_play():
    """Guest play - create temporary session without account"""
    # Create a guest session
    session['user_id'] = None
    session['username'] = 'Guest'
    session['is_guest'] = True
    return redirect(url_for('main'))

@auth_bp.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    return redirect(url_for('auth.launch'))


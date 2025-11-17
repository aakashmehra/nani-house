from flask import Flask, render_template, url_for, request, redirect, session, flash, jsonify
from models import (
    db, init_db, User, Player, House, HousePlayer, Shop,
    PlayerCharacter, PlayerDice, PlayerChest,
    Character, Dice, Chest, FriendRequest, Game
)
from auth import auth_bp
from dotenv import load_dotenv
from datetime import datetime
from flask_socketio import SocketIO, emit, join_room, leave_room
import os, string, random, uuid, json_manager
from collections import defaultdict
from shop import shop_bp
from game_manager import GameManager
from classes.dice import FortuneCore, RiskRoller, BlazeCube, FrostPrism, DoubleFortuneCore

dices = {
    1: FortuneCore(),
    2: RiskRoller(),
    3: BlazeCube(),
    4: FrostPrism(),
    5: DoubleFortuneCore()
}
# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.register_blueprint(shop_bp)

# PostgreSQL database configuration
# Get database URL from environment variable or use default
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost:5432/battle_lanes')

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')

# Initialize database
init_db(app)

app.register_blueprint(auth_bp)

socketio = SocketIO(app, cors_allowed_origins="*", manage_session=False)

DATA_DIR = os.path.join(os.getcwd(), "matches")
os.makedirs(DATA_DIR, exist_ok=True)
def match_path(match_id):
    return os.path.join(DATA_DIR, f"match_{match_id}.json")
# In-memory active games: match_id -> GameManager
active_games: dict = {}
pending_friend_house_requests: dict[int, dict[int, dict]] = defaultdict(dict)

def new_match_uuid():
    return str(uuid.uuid4())


@socketio.on('join_game')
def handle_join_game(data):
    """
    Client should send { match_id: int, player_id: str, char_type: optional }.
    We'll use session user/player fallback if player_id not provided.
    """
    sid = request.sid
    match_id = data.get('match_id')
    raw_player_id = data.get('player_id') or session.get('user_id')
    if not raw_player_id:
        emit('error', {'message': 'no player id provided'})
        return

    player_id_str = str(raw_player_id)
    try:
        numeric_user_id = int(raw_player_id)
    except (TypeError, ValueError):
        numeric_user_id = None

    gm = active_games.get(match_id)

    from classes.characters import Characters
    char = Characters()

    player_record: Player | None = None
    if numeric_user_id is not None:
        player_record = Player.query.filter_by(user_id=numeric_user_id).first()

    equipped_character_id = 1
    if player_record and player_record.equipped_character:
        equipped_character_id = player_record.equipped_character

    db_char = Character.query.get(equipped_character_id)
    if db_char:
        char.name = db_char.name
        char.character_id = db_char.id
        char.image_path = db_char.image_path
        char.type = db_char.character_type

    path = match_path(match_id)

    try:
        pos = gm.spawn_player(player_id_str, char)
    except:
        data = json_manager.read_json(path)
        turn_order = data["turn_order"]
        e_char = json_manager.characters[data["players"][raw_player_id]["id"]]
        room = f"match_{match_id}"
        join_room(room)
        socketio.emit('match_snapshot', data, room=room)
        socketio.emit('turn_update', {"turn": turn_order[data["current_turn_index"]], "user": data["players"][turn_order[0]]["user"]}, room=room)
        socketio.emit('health_update', {"current_health": data["players"][raw_player_id]["health"], "max_health": e_char.health, "user_id": raw_player_id}, room=room)
        return

    print(f"Player {player_id_str} joined match {match_id} at position {pos}")
    # persist snapshot to file
    turn_order = json_manager.gen_turn_order(path)
    json_manager.add_pos(path, raw_player_id, pos)
    
    # join socket room for match
    room = f"match_{match_id}"
    join_room(room)
    data = json_manager.read_json(path)
    e_char = json_manager.characters[data["players"][raw_player_id]["id"]]
    
    socketio.emit('match_snapshot', data, room=room)
    socketio.emit('turn_update', {"turn": turn_order[0], "user": data["players"][turn_order[0]]["user"]}, room=room)
    socketio.emit('health_update', {"current_health": data["players"][raw_player_id]["health"], "max_health": e_char.health}, room=room)

@socketio.on('move_request')
def handle_move_request(data):
    """
    Client sends { match_id, player_id, target: [x,y], steps_allowed: optional }
    """
    match_id = data.get('match_id')
    player_id = data.get('player_id') or session.get('user_id')
    target = data.get('target')
    if not (match_id and player_id and target):
        emit('move_failed', {'reason': 'missing_params'})
        return

    gm = active_games.get(match_id)
    if gm is None:
        emit('move_failed', {'reason': 'match_not_active'})
        return

    target_pos = [target[0], target[1]]
    path = match_path(match_id)
    json_manager.add_pos(path, player_id, target_pos)
    data = json_manager.read_json(path)

    if data:
        room = f"match_{match_id}"
        total_players = data["player_count"]
        next_turn_ind = data["current_turn_index"] + 1
        turn_order = data["turn_order"]

        if next_turn_ind > (total_players - 1):
            next_turn_ind = 0

        json_manager.modify_json(path, ["current_turn_index"], next_turn_ind)
        socketio.emit('turn_update', {"turn":turn_order[next_turn_ind], "user": data["players"][turn_order[next_turn_ind]]["user"]}, room=room)

        socketio.emit('match_snapshot', data, room=room)
    else:    
        emit('move_failed', {'reason': 'invalid_move'})


@socketio.on('roll_request')
def handle_roll_request(data):
    """
    Client: { match_id, player_id }
    Server will use the player's Character.dice (if present) to roll and return the value.
    """
    match_id = data.get('match_id')
    player_id = data.get('player_id') or session.get('user_id')
    if not player_id or match_id is None:
        emit('roll_result', {'reason': 'missing_params'})
        return

    gm = active_games.get(match_id)
    if gm is None:
        emit('roll_result', {'reason': 'match_not_active'})
        return
    path = match_path(match_id)
    data = json_manager.read_json(path)
    dice_id = data["players"][player_id]["dice_id"]
    user = data["players"][player_id]["user"]
    player_dice = dices[dice_id]

    try:
        value = player_dice.roll()
    except Exception:
        value = FortuneCore().roll()

    room = f"match_{match_id}"
    socketio.emit('roll_result', {"user": user, "value": value, "user_id": player_id}, room=room)

@socketio.on('attack_request')
def handle_attack_request(data):
    """Handle attack request - calculate attackable positions"""
    match_id = data.get('match_id')
    player_id = str(data.get('player_id') or session.get('user_id'))
    if not player_id or match_id is None:
        emit('attackable_players', {'attackable_positions': []})
        return

    gm = active_games.get(match_id)
    if gm is None:
        emit('attackable_players', {'attackable_positions': []})
        return

    path = match_path(match_id)
    game_data = json_manager.read_json(path)
    
    if player_id not in game_data["players"]:
        emit('attackable_players', {'attackable_positions': []})
        return

    attacker_data = game_data["players"][player_id]
    attacker_pos = attacker_data["position"]
    character_id = attacker_data["id"]
    
    # Get character object from json_manager
    character = json_manager.characters.get(character_id)
    if not character:
        emit('attackable_players', {'attackable_positions': []})
        return

    # Get character range
    char_range = character.range
    if isinstance(char_range, list) and len(char_range) == 2:
        min_range, max_range = char_range[0], char_range[1]
    else:
        min_range, max_range = 0, int(char_range) if isinstance(char_range, (int, float)) else 1

    # Calculate attackable positions
    attackable_positions = []
    for pid, pdata in game_data["players"].items():
        if pid == player_id:
            continue
        target_pos = pdata.get("position")
        if not target_pos:
            continue
        
        # Calculate distance (Manhattan distance)
        distance = abs(target_pos[0] - attacker_pos[0]) + abs(target_pos[1] - attacker_pos[1])
        
        if min_range <= distance <= max_range:
            attackable_positions.append(target_pos)

    room = f"match_{match_id}"
    socketio.emit('attackable_players', {
        'attackable_positions': attackable_positions,
        'attacker_id': player_id
    }, room=room)

@socketio.on('attack_target')
def handle_attack_target(data):
    """Handle attack execution"""
    match_id = data.get('match_id')
    attacker_id = str(data.get('attacker_id') or session.get('user_id'))
    target_id = str(data.get('target_id'))
    
    if not attacker_id or not target_id or match_id is None:
        emit('attack_result', {'success': False, 'message': 'Invalid attack parameters'})
        return

    gm = active_games.get(match_id)
    if gm is None:
        emit('attack_result', {'success': False, 'message': 'Match not active'})
        return

    path = match_path(match_id)
    game_data = json_manager.read_json(path)
    
    if attacker_id not in game_data["players"] or target_id not in game_data["players"]:
        emit('attack_result', {'success': False, 'message': 'Player not found'})
        return

    attacker_data = game_data["players"][attacker_id]
    target_data = game_data["players"][target_id]
    
    # Get character objects
    attacker_char_id = attacker_data["id"]
    target_char_id = target_data["id"]
    
    attacker_char = json_manager.characters.get(attacker_char_id)
    target_char = json_manager.characters.get(target_char_id)
    
    if not attacker_char or not target_char:
        emit('attack_result', {'success': False, 'message': 'Character not found'})
        return

    # Set health and shield from JSON
    target_char.health = target_data["health"]
    target_char.shield = target_data.get("shield", 0)
    
    # Get max health from JSON
    max_health = target_data.get("max_health", target_char.health)
    
    # Perform attack
    attacker_char.attack_target(target_char)
    
    # Update JSON with new health and shield
    target_data["health"] = target_char.health
    target_data["shield"] = target_char.shield
    
    json_manager.modify_json(path, ["players", target_id, "health"], target_char.health)
    json_manager.modify_json(path, ["players", target_id, "shield"], target_char.shield)
    
    # Emit health update
    room = f"match_{match_id}"
    socketio.emit('health_update', {
        "current_health": target_char.health,
        "max_health": max_health,
        "user_id": target_id
    }, room=room)
    
    # Move to next turn
    game_data = json_manager.read_json(path)
    total_players = game_data["player_count"]
    next_turn_ind = game_data["current_turn_index"] + 1
    turn_order = game_data["turn_order"]
    
    if next_turn_ind > (total_players - 1):
        next_turn_ind = 0
    
    json_manager.modify_json(path, ["current_turn_index"], next_turn_ind)
    socketio.emit('turn_update', {
        "turn": turn_order[next_turn_ind],
        "user": game_data["players"][turn_order[next_turn_ind]]["user"]
    }, room=room)
    
    socketio.emit('match_snapshot', game_data, room=room)
    emit('attack_result', {'success': True, 'message': 'Attack successful'})
    


# Socket events
@socketio.on('connect')
def handle_connect(auth):
    sid = request.sid
    app.logger.info(f"[SOCKET] connect sid={sid} auth={auth} session_user={session.get('user_id')}")
    # If client sent auth (fallback), show it
    if auth:
        app.logger.info(f"[SOCKET] auth provided: {auth}")

@socketio.on('join_house')
def handle_join_house(data):
    sid = request.sid
    app.logger.info(f"[SOCKET] join_house called sid={sid} data={data} session_user={session.get('user_id')}")
    house_code = data.get('house_code')
    # Try to find house and membership
    house = House.query.filter_by(house_code=house_code).first() if house_code else None
    if not house:
        emit('error', {'message': 'House not found'})
        app.logger.info(f"[SOCKET] house not found for code={house_code}")
        return

    # Try to find player via session
    user_id = session.get('user_id')
    player = Player.query.filter_by(user_id=int(user_id)).first() if user_id else None

    # If session-based lookup failed, allow auth fallback from data
    if not player and 'auth_user_id' in data:
        try:
            auth_uid = int(data.get('auth_user_id'))
            player = Player.query.filter_by(user_id=auth_uid).first()
            app.logger.info(f"[SOCKET] fallback auth_user_id used: {auth_uid}")
        except Exception as e:
            app.logger.exception("Invalid auth_user_id fallback")

    if not player:
        emit('error', {'message': 'Player not found or not authenticated'})
        app.logger.info(f"[SOCKET] Player not found sid={sid}, session_user={user_id}")
        return

    membership = HousePlayer.query.filter_by(house_id=house.id, player_id=player.id).first()
    if not membership:
        emit('error', {'message': 'Not a member of this house'})
        app.logger.info(f"[SOCKET] membership missing for player {player.id} in house {house.id}")
        return

    room = f"house_{house.id}"
    join_room(room)
    app.logger.info(f"[SOCKET] sid={sid} player={player.id} joined room={room}")

    emit('joined', {'house_id': house.id, 'status': house.status, 'current_players': house.current_players})


@socketio.on('leave_house')
def on_leave_house(data):
    house_code = data.get('house_code')
    house = House.query.filter_by(house_code=house_code).first()
    if not house:
        return
    leave_room(f"house_{house.id}")

@socketio.on('disconnect')
def on_disconnect():
    app.logger.debug(f"Socket disconnected: sid={request.sid}")


@socketio.on('register_user')
def handle_register_user(data):
    """Associate this socket with a user-specific room."""
    user_id = data.get('user_id') or session.get('user_id')
    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        emit('register_user_ack', {'success': False, 'error': 'invalid_user'})
        return

    join_room(f"user_{user_id}")
    emit('register_user_ack', {'success': True, 'user_id': user_id})


@socketio.on('house_friend_request_send')
def handle_house_friend_request_send(data):
    """Handle websocket friend join requests."""
    session_user_id = session.get('user_id')
    if not session_user_id:
        emit('house_friend_request_status', {'success': False, 'error': 'not_authenticated'})
        return

    try:
        requester_user_id = int(session_user_id)
    except (TypeError, ValueError):
        emit('house_friend_request_status', {'success': False, 'error': 'invalid_user'})
        return

    requester_user = User.query.get(requester_user_id)
    if not requester_user:
        emit('house_friend_request_status', {'success': False, 'error': 'user_not_found'})
        return

    target_user_id = data.get('target_user_id')
    house_code = data.get('house_code')

    try:
        target_user_id = int(target_user_id)
    except (TypeError, ValueError):
        emit('house_friend_request_status', {'success': False, 'error': 'invalid_target'})
        return

    if target_user_id == requester_user_id:
        emit('house_friend_request_status', {'success': False, 'error': 'cannot_request_self'})
        return

    if target_user_id not in requester_user.get_friends_list():
        emit('house_friend_request_status', {'success': False, 'error': 'not_friends'})
        return

    target_player = Player.query.filter_by(user_id=target_user_id).first()
    if not target_player:
        emit('house_friend_request_status', {'success': False, 'error': 'target_player_missing'})
        return

    house_query = House.query.filter_by(created_by=target_player.id, status='waiting')
    if house_code:
        house_query = house_query.filter_by(house_code=house_code)
    house = house_query.first()
    if not house:
        emit('house_friend_request_status', {'success': False, 'error': 'house_not_available'})
        return

    if house.current_players >= house.max_players:
        emit('house_friend_request_status', {'success': False, 'error': 'house_full'})
        return

    requester_player = Player.query.filter_by(user_id=requester_user_id).first()
    if not requester_player:
        emit('house_friend_request_status', {'success': False, 'error': 'player_not_found'})
        return

    existing_membership = HousePlayer.query.filter_by(house_id=house.id, player_id=requester_player.id).first()
    if existing_membership:
        emit('house_friend_request_status', {'success': False, 'error': 'already_in_house'})
        return

    pending_friend_house_requests[target_user_id][requester_user_id] = {
        "house_id": house.id,
        "house_code": house.house_code,
        "requested_at": datetime.utcnow()
    }

    payload = {
        "requester_user_id": requester_user_id,
        "requester_username": requester_user.username,
        "house_code": house.house_code,
        "house_name": house.name
    }
    socketio.emit('house_friend_request_received', payload, room=f"user_{target_user_id}")
    emit('house_friend_request_status', {'success': True, 'target_user_id': target_user_id, 'house_code': house.house_code})


@socketio.on('house_friend_request_response')
def handle_house_friend_request_response(data):
    """Process accept/reject decisions from house owners."""
    session_user_id = session.get('user_id')
    if not session_user_id:
        emit('house_friend_request_update', {'success': False, 'error': 'not_authenticated'})
        return

    try:
        responder_user_id = int(session_user_id)
    except (TypeError, ValueError):
        emit('house_friend_request_update', {'success': False, 'error': 'invalid_user'})
        return

    requester_user_id = data.get('requester_user_id')
    decision = (data.get('decision') or '').lower()

    try:
        requester_user_id = int(requester_user_id)
    except (TypeError, ValueError):
        emit('house_friend_request_update', {'success': False, 'error': 'invalid_requester'})
        return

    pending_for_user = pending_friend_house_requests.get(responder_user_id, {})
    pending_entry = pending_for_user.get(requester_user_id)

    if not pending_entry:
        emit('house_friend_request_update', {'success': False, 'error': 'request_not_found'})
        return

    house = House.query.get(pending_entry['house_id'])
    requester_player = Player.query.filter_by(user_id=requester_user_id).first()

    if decision not in {'accept', 'reject'}:
        emit('house_friend_request_update', {'success': False, 'error': 'invalid_decision'})
        return

    if not house or not requester_player:
        pending_for_user.pop(requester_user_id, None)
        emit('house_friend_request_update', {'success': False, 'error': 'house_or_player_missing'})
        socketio.emit('house_friend_request_result', {
            'status': 'cancelled',
            'reason': 'house_or_player_missing'
        }, room=f"user_{requester_user_id}")
        return

    if decision == 'reject':
        pending_for_user.pop(requester_user_id, None)
        emit('house_friend_request_update', {
            'success': True,
            'decision': 'rejected',
            'requester_user_id': requester_user_id
        })
        socketio.emit('house_friend_request_result', {
            'status': 'rejected',
            'house_code': house.house_code
        }, room=f"user_{requester_user_id}")
        return

    if house.status != 'waiting':
        pending_for_user.pop(requester_user_id, None)
        emit('house_friend_request_update', {'success': False, 'error': 'house_not_accepting'})
        socketio.emit('house_friend_request_result', {
            'status': 'rejected',
            'reason': 'house_not_accepting'
        }, room=f"user_{requester_user_id}")
        return

    if house.current_players >= house.max_players:
        pending_for_user.pop(requester_user_id, None)
        emit('house_friend_request_update', {'success': False, 'error': 'house_full'})
        socketio.emit('house_friend_request_result', {
            'status': 'rejected',
            'reason': 'house_full'
        }, room=f"user_{requester_user_id}")
        return

    existing_membership = HousePlayer.query.filter_by(house_id=house.id, player_id=requester_player.id).first()
    if existing_membership:
        pending_for_user.pop(requester_user_id, None)
        emit('house_friend_request_update', {'success': False, 'error': 'already_in_house'})
        socketio.emit('house_friend_request_result', {
            'status': 'accepted',
            'house_code': house.house_code,
            'redirect_url': url_for('create_house')
        }, room=f"user_{requester_user_id}")
        return

    try:
        new_membership = HousePlayer(
            house_id=house.id,
            player_id=requester_player.id,
            is_ready=False
        )
        db.session.add(new_membership)
        house.current_players = (house.current_players or 0) + 1
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        pending_for_user.pop(requester_user_id, None)
        emit('house_friend_request_update', {'success': False, 'error': 'database_error', 'detail': str(exc)})
        socketio.emit('house_friend_request_result', {
            'status': 'rejected',
            'reason': 'database_error'
        }, room=f"user_{requester_user_id}")
        return

    pending_for_user.pop(requester_user_id, None)

    emit('house_friend_request_update', {
        'success': True,
        'decision': 'accepted',
        'requester_user_id': requester_user_id
    })

    socketio.emit('house_friend_request_result', {
        'status': 'accepted',
        'house_code': house.house_code,
        'house_name': house.name,
        'redirect_url': url_for('create_house')
    }, room=f"user_{requester_user_id}")

    room_name = f"house_{house.id}"
    payload = {
        "house_id": house.id,
        "player_id": requester_player.id,
        "player_name": requester_player.username,
        "current_players": house.current_players
    }
    socketio.emit('player_joined', payload, room=room_name)


def get_user_coins():
    """Helper function to get current user's coins from database"""
    user_id = session.get('user_id')
    
    # Check if user is guest or not logged in
    if not user_id or session.get('is_guest'):
        return 0
    
    try:
        # Ensure user_id is an integer
        user_id = int(user_id)
        
        # Query Player directly by user_id
        player = Player.query.filter_by(user_id=user_id).first()
        if player:
            return int(player.coins) if player.coins is not None else 0
        
        # If no player record exists, create one with 100 coins
        # This shouldn't happen if login works correctly, but just in case
        user = User.query.get(user_id)
        if user:
            new_player = Player(
                user_id=user_id,
                coins=100,
                wins=0,
                losses=0,
                total_games=0
            )
            db.session.add(new_player)
            db.session.commit()
            return 100
        
        return 0
    except Exception as e:
        # If there's an error, return 0
        print(f"Error getting user coins: {e}")
        return 0



@app.route('/')
def home():
    """Home / Landing page"""
    return render_template('index.html')

@app.route('/how_to_play')
def how_to_play():
    """How to Play page"""
    return render_template('how_to_play.html')

@app.route('/about')
def about():
    """About page"""
    return render_template('about.html')

@app.route('/main')
def main():
    """Main page - requires authentication or guest"""
    if 'user_id' not in session and 'is_guest' not in session:
        return redirect(url_for('auth.launch'))
    
    coin_value = get_user_coins()
    return render_template('launch.html', coin_value=coin_value)

@app.route('/house_page')
def house_page():
    """House page - shows create or my house button"""
    if 'user_id' not in session or session.get('is_guest'):
        return redirect(url_for('auth.launch'))
    
    user_id = session.get('user_id')
    player = Player.query.filter_by(user_id=user_id).first()
    
    user_house = None
    if player:
        user_house = House.query.filter_by(created_by=player.id).first()
    
    return render_template('house_page.html', user_house=user_house)

# Settings is now a popup in launch.html, no separate route needed

@app.route('/inventory')
def inventory():
    coin_value = get_user_coins()
    return render_template('inventory.html', coin_value=coin_value)

@app.route('/characters')
def characters():
    # require login (same rules you already use elsewhere)
    if 'user_id' not in session or session.get('is_guest'):
        return redirect(url_for('auth.launch'))

    user_id = session.get('user_id')
    player = Player.query.filter_by(user_id=user_id).first()
    coin_value = get_user_coins()
    
    # Get all characters from the database
    all_characters = Character.query.all()
    
    # Get player's unlocked characters (any character they have gained, regardless of unlocked status)
    player_character_ids = set()
    if player:
        player_chars = PlayerCharacter.query.filter_by(player_id=player.id).all()
        player_character_ids = {pc.character_id for pc in player_chars}
    
    # Build items list with all characters, marking locked/unlocked
    items = []
    for char in all_characters:
        is_unlocked = char.id in player_character_ids
        player_char = None
        if is_unlocked and player:
            player_char = PlayerCharacter.query.filter_by(
                player_id=player.id, 
                character_id=char.id
            ).first()
        
        # Get image path from database
        image_filename = char.image_path
        # Remove 'img/characters/' prefix if present, we'll add it in template
        if image_filename and image_filename.startswith('img/characters/'):
            image_filename = image_filename.replace('img/characters/', '')
        elif image_filename and image_filename.startswith('img/'):
            image_filename = image_filename.replace('img/', '')
        
        is_equipped = bool(player and player.equipped_character == char.id)

        items.append({
            "player_item_id": player_char.id if player_char else None,
            "def_id": char.id,
            "name": char.name,
            "qty": 1,
            "description": char.description or "",
            "image": f"img/characters/{image_filename}" if image_filename else "img/characters/default.webp",
            "is_locked": not is_unlocked,
            "is_equipped": is_equipped,
            "meta": {
                "unlocked": player_char.unlocked if player_char else False,
                "obtained_at": player_char.obtained_at if player_char else None
            }
        })

    return render_template('grid_page.html',
                           page_title='CHARACTERS',
                           coin_value=coin_value,
                           back_url=url_for('inventory'),
                           items=items,
                           equipped_character=player.equipped_character if player else 1)


@app.route('/equip_character', methods=['POST'])
def equip_character():
    if 'user_id' not in session or session.get('is_guest'):
        return jsonify(success=False, error='not_authenticated'), 401

    user_id = session.get('user_id')
    player = Player.query.filter_by(user_id=user_id).first()
    if not player:
        return jsonify(success=False, error='player_not_found'), 404

    data = request.get_json(silent=True) or {}
    character_id = data.get('character_id')
    if not character_id:
        return jsonify(success=False, error='character_id_required'), 400

    try:
        character_id = int(character_id)
    except (TypeError, ValueError):
        return jsonify(success=False, error='invalid_character_id'), 400

    # Check if character exists
    character = Character.query.get(character_id)
    if not character:
        return jsonify(success=False, error='character_not_found'), 404

    # Check if player owns this character (has it in their inventory)
    owned_character = PlayerCharacter.query.filter_by(
        player_id=player.id,
        character_id=character_id
    ).first()
    if not owned_character:
        return jsonify(success=False, error='character_not_owned'), 403

    # Update equipped character in database
    try:
        player.equipped_character = character_id
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        return jsonify(success=False, error='database_error', detail=str(exc)), 500

    return jsonify(success=True, equipped_character=character_id)


@app.route('/dice')
def dice():
    if 'user_id' not in session or session.get('is_guest'):
        return redirect(url_for('auth.launch'))

    user_id = session.get('user_id')
    player = Player.query.filter_by(user_id=user_id).first()
    if not player:
        coin_value = get_user_coins()
        return render_template('grid_page.html',
                               page_title='DICE',
                               coin_value=coin_value,
                               back_url=url_for('inventory'),
                               items=[])

    pds = PlayerDice.query.filter_by(player_id=player.id).join(Dice).all()
    items = []
    for pd in pds:
        d = pd.dice
        items.append({
            "player_item_id": pd.id,
            "def_id": d.id,
            "name": d.name,
            "image": d.image_path or "img/dice/default_dice.webp",
            "qty": pd.quantity,
            "description": d.effect or "",
            "price": d.price,
            "meta": {"rarity": d.rarity}
        })

    coin_value = player.coins
    return render_template('grid_page.html',
                           page_title='DICE',
                           coin_value=coin_value,
                           back_url=url_for('inventory'),
                           items=items)


@app.route('/packs')
def packs():
    if 'user_id' not in session or session.get('is_guest'):
        return redirect(url_for('auth.launch'))

    user_id = session.get('user_id')
    player = Player.query.filter_by(user_id=user_id).first()
    if not player:
        coin_value = get_user_coins()
        return render_template('grid_page.html',
                               page_title='PACKS',
                               coin_value=coin_value,
                               back_url=url_for('inventory'),
                               items=[])

    pcs = PlayerChest.query.filter_by(player_id=player.id).join(Chest).all()
    items = []
    for pc in pcs:
        c = pc.chest
        items.append({
            "player_item_id": pc.id,
            "def_id": c.id,
            "name": c.name,
            "image": c.image_path or "img/chests/default_chest.webp",
            "qty": pc.quantity,
            "description": c.description or "",
            "price": c.price,
            "meta": {"chest_type": c.chest_type}
        })

    coin_value = player.coins
    return render_template('grid_page.html',
                           page_title='PACKS',
                           coin_value=coin_value,
                           back_url=url_for('inventory'),
                           items=items)

@app.route('/items')
def items():
    if 'user_id' not in session or session.get('is_guest'):
        return redirect(url_for('auth.launch'))

    user_id = session.get('user_id')
    player = Player.query.filter_by(user_id=user_id).first()
    if not player:
        coin_value = get_user_coins()
        return render_template('grid_page.html',
                               page_title='ITEMS',
                               coin_value=coin_value,
                               back_url=url_for('inventory'),
                               items=[])

    # TODO: Implement PlayerItem model and query when Item model is created
    # For now, return empty items list
    items = []
    
    coin_value = get_user_coins()
    return render_template('grid_page.html',
                           page_title='ITEMS',
                           coin_value=coin_value,
                           back_url=url_for('inventory'),
                           items=items)


@app.route('/profile', methods=['GET', 'POST'])
def profile():
    """Profile page - view and edit user profile"""
    if 'user_id' not in session or session.get('is_guest'):
        return redirect(url_for('auth.launch'))
    
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user:
        return redirect(url_for('auth.launch'))
    
    error = None
    
    if request.method == 'POST':
        # Update username if provided
        new_username = request.form.get('username', '').strip()
        if not new_username:
            error = 'Username cannot be empty'
        elif new_username != user.username:
            # Check if username already exists
            existing_user = User.query.filter_by(username=new_username).first()
            if existing_user and existing_user.id != user.id:
                error = 'Username already exists'
            elif len(new_username) < 3:
                error = 'Username must be at least 3 characters'
            elif len(new_username) > 80:
                error = 'Username must be less than 80 characters'
            else:
                user.username = new_username
                session['username'] = new_username
                db.session.commit()
    
    # Get player data for stats
    player = Player.query.filter_by(user_id=user_id).first()
    wins = player.wins if player else 0
    losses = player.losses if player else 0
    total_games = player.total_games if player else 0
    
    # Get pending friend request count
    pending_count = FriendRequest.query.filter_by(
        to_user_id=user_id,
        status='pending'
    ).count()
    
    # Get total matches played across the entire game server
    total_server_matches = Game.query.count()
    
    return render_template('profile.html', user=user, error=error, wins=wins, losses=losses, total_games=total_games, pending_friend_requests=pending_count, total_server_matches=total_server_matches)

@app.route('/transfer_coins', methods=['POST'])
def transfer_coins():
    """Transfer coins from current user to another user by username"""
    if 'user_id' not in session or session.get('is_guest'):
        return jsonify(success=False, error='not_authenticated'), 401
    
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user:
        return jsonify(success=False, error='user_not_found'), 404
    
    try:
        # Get raw data for debugging
        raw_data = request.get_data(as_text=True)
        print(f"DEBUG transfer_coins: Raw request data: {raw_data}")
        print(f"DEBUG transfer_coins: Content-Type: {request.content_type}")
        
        data = request.get_json(silent=True) or {}
        print(f"DEBUG transfer_coins: Parsed JSON data: {data}")
        
        to_username = data.get('to_username', '').strip() if data.get('to_username') else ''
        amount = data.get('amount')
        
        print(f"DEBUG transfer_coins: to_username='{to_username}', amount={amount} (type: {type(amount)})")
        
        if not to_username:
            return jsonify(success=False, error='username_required', detail='Recipient username is required'), 400
        
        if amount is None:
            return jsonify(success=False, error='invalid_amount', detail='Amount is required'), 400
        
        try:
            amount = int(amount)
        except (ValueError, TypeError) as e:
            return jsonify(success=False, error='invalid_amount', detail=f'Amount must be a number, got: {type(amount).__name__} ({amount})'), 400
        
        if amount <= 0:
            return jsonify(success=False, error='amount_must_be_positive', detail='Amount must be greater than 0'), 400
        
        print(f"DEBUG transfer_coins: Calling Player.transfer_coins('{user.username}', '{to_username}', {amount})")
        result = Player.transfer_coins(user.username, to_username, amount)
        print(f"DEBUG transfer_coins: Result: {result}")
        
        if result['success']:
            db.session.commit()
            return jsonify(success=True, 
                          from_coins=result['from_coins'], 
                          to_coins=result['to_coins'],
                          message=f'Successfully transferred {amount} coins to {to_username}')
        else:
            error_code = result.get('error', 'transfer_failed')
            # Map error codes to user-friendly messages
            if error_code == 'insufficient_funds':
                current_coins = result.get('current_coins')
                required = result.get('required', amount)
                if current_coins is not None:
                    error_msg = f'Insufficient coins. You have {current_coins} coins.'
                else:
                    error_msg = f'Insufficient coins. You need {required} coins but have less.'
            elif error_code == 'cannot_transfer_to_self':
                error_msg = 'You cannot transfer coins to yourself'
            elif error_code == 'sender_not_found':
                error_msg = 'Your account was not found'
            elif error_code == 'recipient_not_found':
                error_msg = f'User "{to_username}" not found'
            elif error_code == 'recipient_player_not_found':
                error_msg = f'Player account for "{to_username}" not found'
            elif error_code == 'transfer_failed':
                error_msg = 'Transfer failed. Please try again.'
            else:
                error_msg = error_code.replace('_', ' ').title()
            
            return jsonify(success=False, error=error_code, detail=error_msg), 400
    except Exception as e:
        import traceback
        print(f"DEBUG transfer_coins: Exception: {e}")
        traceback.print_exc()
        db.session.rollback()
        return jsonify(success=False, error='unexpected_error', detail=str(e)), 500

@app.route('/send_friend_request', methods=['POST'])
def send_friend_request():
    """Send a friend request to another user by username"""
    if 'user_id' not in session or session.get('is_guest'):
        return jsonify(success=False, error='not_authenticated'), 401
    
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user:
        return jsonify(success=False, error='user_not_found'), 404
    
    try:
        data = request.get_json(silent=True) or {}
        to_username = data.get('username', '').strip()
        
        if not to_username:
            return jsonify(success=False, error='username_required'), 400
        
        # Check if user is trying to add themselves
        if to_username.lower() == user.username.lower():
            return jsonify(success=False, error='cannot_add_self'), 400
        
        # Find the target user
        target_user = User.query.filter_by(username=to_username).first()
        if not target_user:
            return jsonify(success=False, error='user_not_found'), 404
        
        # Check if already friends
        if target_user.id in user.get_friends_list():
            return jsonify(success=False, error='already_friends'), 400
        
        # Check if there's already a pending request
        existing_request = FriendRequest.query.filter(
            ((FriendRequest.from_user_id == user.id) & (FriendRequest.to_user_id == target_user.id)) |
            ((FriendRequest.from_user_id == target_user.id) & (FriendRequest.to_user_id == user.id))
        ).filter_by(status='pending').first()
        
        if existing_request:
            return jsonify(success=False, error='request_already_exists'), 400
        
        # Create new friend request
        friend_request = FriendRequest(
            from_user_id=user.id,
            to_user_id=target_user.id,
            status='pending'
        )
        db.session.add(friend_request)
        db.session.commit()
        
        return jsonify(success=True, message='Friend request sent')
    except Exception as e:
        db.session.rollback()
        return jsonify(success=False, error='unexpected_error', detail=str(e)), 500

@app.route('/get_friends', methods=['GET'])
def get_friends():
    """Get current friends list for the current user"""
    if 'user_id' not in session or session.get('is_guest'):
        return jsonify(success=False, error='not_authenticated'), 401
    
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user:
        return jsonify(success=False, error='user_not_found'), 404
    
    try:
        friends_list = user.get_friends_list()
        friends_data = []
        
        for friend_id in friends_list:
            friend_user = User.query.get(friend_id)
            if friend_user:
                friends_data.append({
                    'id': friend_user.id,
                    'username': friend_user.username
                })
        
        return jsonify(success=True, friends=friends_data, count=len(friends_data))
    except Exception as e:
        return jsonify(success=False, error='unexpected_error', detail=str(e)), 500


@app.route('/api/friend-houses', methods=['GET'])
def api_friend_houses():
    """Return list of friends who currently host a waiting house."""
    if 'user_id' not in session or session.get('is_guest'):
        return jsonify(success=False, error='not_authenticated'), 401

    user_id = session.get('user_id')
    user = User.query.get(user_id)

    if not user:
        return jsonify(success=False, error='user_not_found'), 404

    try:
        friend_ids = user.get_friends_list()
        if not friend_ids:
            return jsonify(success=True, houses=[], count=0)

        friend_players = Player.query.filter(Player.user_id.in_(friend_ids)).all()
        if not friend_players:
            return jsonify(success=True, houses=[], count=0)

        player_ids = [p.id for p in friend_players]

        houses = House.query.filter(
            House.created_by.in_(player_ids),
            House.status == 'waiting'
        ).all()

        house_data = []
        for house in houses:
            host_player = next((p for p in friend_players if p.id == house.created_by), None)
            if not host_player:
                continue
            host_user = host_player.user
            house_data.append({
                "friend_user_id": host_player.user_id,
                "friend_username": host_user.username if host_user else "Friend",
                "house_code": house.house_code,
                "house_name": house.name,
                "current_players": house.current_players or 0,
                "max_players": house.max_players,
                "status": house.status
            })

        return jsonify(success=True, houses=house_data, count=len(house_data))
    except Exception as exc:
        return jsonify(success=False, error='unexpected_error', detail=str(exc)), 500

@app.route('/get_friend_stats', methods=['GET'])
def get_friend_stats():
    """Get stats (wins, losses, total games) for a friend"""
    if 'user_id' not in session or session.get('is_guest'):
        return jsonify(success=False, error='not_authenticated'), 401
    
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user:
        return jsonify(success=False, error='user_not_found'), 404
    
    try:
        friend_id = request.args.get('friend_id')
        if not friend_id:
            return jsonify(success=False, error='friend_id_required'), 400
        
        friend_id = int(friend_id)
        
        # Verify the friend is actually in the user's friends list
        if friend_id not in user.get_friends_list():
            return jsonify(success=False, error='not_friends'), 403
        
        # Get friend's player stats
        friend_player = Player.query.filter_by(user_id=friend_id).first()
        if not friend_player:
            return jsonify(success=True, wins=0, losses=0, total_games=0)
        
        return jsonify(success=True, 
                       wins=friend_player.wins or 0,
                       losses=friend_player.losses or 0,
                       total_games=friend_player.total_games or 0)
    except Exception as e:
        return jsonify(success=False, error='unexpected_error', detail=str(e)), 500

@app.route('/remove_friend', methods=['POST'])
def remove_friend():
    """Remove a friend from the current user's friends list"""
    if 'user_id' not in session or session.get('is_guest'):
        return jsonify(success=False, error='not_authenticated'), 401
    
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user:
        return jsonify(success=False, error='user_not_found'), 404
    
    try:
        data = request.get_json(silent=True) or {}
        friend_id = data.get('friend_id')
        
        if not friend_id:
            return jsonify(success=False, error='friend_id_required'), 400
        
        friend_id = int(friend_id)
        
        # Remove friend from current user's list
        if user.remove_friend(friend_id):
            # Also remove current user from friend's list
            friend_user = User.query.get(friend_id)
            if friend_user:
                friend_user.remove_friend(user_id)
            
            db.session.commit()
            return jsonify(success=True, message='Friend removed')
        else:
            return jsonify(success=False, error='friend_not_found'), 404
    except Exception as e:
        db.session.rollback()
        return jsonify(success=False, error='unexpected_error', detail=str(e)), 500

@app.route('/get_friend_requests', methods=['GET'])
def get_friend_requests():
    """Get pending friend requests for the current user"""
    if 'user_id' not in session or session.get('is_guest'):
        return jsonify(success=False, error='not_authenticated'), 401
    
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user:
        return jsonify(success=False, error='user_not_found'), 404
    
    try:
        # Get pending requests where current user is the recipient
        pending_requests = FriendRequest.query.filter_by(
            to_user_id=user.id,
            status='pending'
        ).all()
        
        requests_data = []
        for req in pending_requests:
            from_user = User.query.get(req.from_user_id)
            if from_user:
                requests_data.append({
                    'id': req.id,
                    'from_username': from_user.username,
                    'from_user_id': from_user.id,
                    'created_at': req.created_at.isoformat()
                })
        
        return jsonify(success=True, requests=requests_data, count=len(requests_data))
    except Exception as e:
        return jsonify(success=False, error='unexpected_error', detail=str(e)), 500

@app.route('/respond_friend_request', methods=['POST'])
def respond_friend_request():
    """Accept or reject a friend request"""
    if 'user_id' not in session or session.get('is_guest'):
        return jsonify(success=False, error='not_authenticated'), 401
    
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user:
        return jsonify(success=False, error='user_not_found'), 404
    
    try:
        data = request.get_json(silent=True) or {}
        request_id = data.get('request_id')
        action = data.get('action')  # 'accept' or 'reject'
        
        if not request_id or action not in ['accept', 'reject']:
            return jsonify(success=False, error='invalid_parameters'), 400
        
        # Find the friend request
        friend_request = FriendRequest.query.get(request_id)
        if not friend_request:
            return jsonify(success=False, error='request_not_found'), 404
        
        # Verify the request is for the current user
        if friend_request.to_user_id != user.id:
            return jsonify(success=False, error='unauthorized'), 403
        
        # Verify the request is still pending
        if friend_request.status != 'pending':
            return jsonify(success=False, error='request_already_processed'), 400
        
        if action == 'accept':
            # Add each other as friends
            from_user = User.query.get(friend_request.from_user_id)
            if from_user:
                user.add_friend(from_user.id)
                from_user.add_friend(user.id)
                friend_request.status = 'accepted'
                db.session.commit()
                return jsonify(success=True, message='Friend request accepted')
            else:
                return jsonify(success=False, error='sender_not_found'), 404
        else:  # reject
            friend_request.status = 'rejected'
            db.session.commit()
            return jsonify(success=True, message='Friend request rejected')
    except Exception as e:
        db.session.rollback()
        return jsonify(success=False, error='unexpected_error', detail=str(e)), 500

@app.route('/game')
def game():
    match_id = request.args.get('match_id')
    return render_template('game.html', MATCH_ID=match_id, AUTH_USER_ID=session.get('user_id'))

@app.route('/shop')
def shop():
    coin_value = get_user_coins()
    shop_items = Shop.query.filter_by(is_active=True).all()
    # Convert shop items to dictionaries for JSON serialization
    shop_items_dict = [{
        'id': item.id,
        'name': item.name,
        'item_type': item.item_type,
        'cost': item.cost,
        'description': item.description or '',
        'image_path': item.image_path or ''
    } for item in shop_items]
    return render_template('shop.html',
                         shop_items=shop_items,
                         shop_items_json=shop_items_dict,
                         coin_value=coin_value,
                         back_url=url_for('main'))

@app.route('/create_house', methods=['GET', 'POST'])
def create_house():
    """Create house page - one house per user, allows delete, shows start game when others join"""
    if 'user_id' not in session or session.get('is_guest'):
        return redirect(url_for('auth.launch'))
    
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user:
        return redirect(url_for('auth.launch'))
    
    # Get player record
    player = Player.query.filter_by(user_id=user_id).first()
    if not player:
        return redirect(url_for('auth.launch'))
    
    # Get house created by this user
    user_house = House.query.filter_by(created_by=player.id).first()
    
    # Check if user joined another house (not created by them)
    joined_house = None
    if not user_house:
        house_player = HousePlayer.query.filter_by(player_id=player.id).first()
        if house_player:
            joined_house = House.query.get(house_player.house_id)
    
    # Check if user is trying to start game
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'start_game' and user_house:
            if user_house.current_players >= 2:
                user_house.status = 'in_progress'
                user_house.started_at = datetime.utcnow()
                match_id = new_match_uuid()
                db.session.commit()
                path = match_path(match_id)

                gm = GameManager(board_size=10)

                # Store it in memory (so sockets can access)
                active_games[match_id] = gm

                # Save initial game state snapshot to JSON file
                json_manager.create_file(path, user_id, match_id)
                

                room_name = f"house_{user_house.id}"
                payload = {
                    "house_id": user_house.id,
                    "started_at": user_house.started_at.isoformat() if user_house.started_at else None,
                    "redirect_url": url_for('game'),
                    "match_id": match_id,
                }

                # Emit to the room
                app.logger.info(f"[SOCKET] emitting game_started to {room_name} payload={payload}")
                socketio.emit('game_started', payload, room=room_name)

                # TEMP DEBUG: also broadcast globally so we can see if clients listen at all
                app.logger.info("[SOCKET] broadcasting debug_game_ping to all clients (temporary)")
                socketio.emit('debug_game_ping', {'msg': 'debug broadcast - server fired'})

                flash('Game started!', 'success')
                display_house = user_house if user_house else joined_house
                if display_house and House.query.get(display_house.id).status == 'in_progress':
                    # only redirect if this player is still a member of that house
                    membership = HousePlayer.query.filter_by(house_id=display_house.id, player_id=player.id).first()
                    if membership:
                        return redirect(url_for('game'))

            else:
                flash('Need at least 2 players to start the game.', 'error')
                return redirect(url_for('create_house'))
        
        # Original create house logic
        if user_house:
            flash('You already have a house. Delete it first to create a new one.', 'error')
            return redirect(url_for('create_house'))
        
        house_name = request.form.get('house_name', '').strip()
        
        # Generate unique house code
        house_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        
        # Ensure code is unique
        while House.query.filter_by(house_code=house_code).first():
            house_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        
        # Create new house
        new_house = House(
            house_code=house_code,
            name=house_name if house_name else f"{user.username}'s House",
            created_by=player.id,
            max_players=6,
            current_players=1,  # Creator is first player
            status='waiting'
        )
        
        db.session.add(new_house)
        db.session.flush()  # Flush to get the house ID
        
        # Add creator as player
        house_player = HousePlayer(
            house_id=new_house.id,
            player_id=player.id,
            is_ready=False
        )
        db.session.add(house_player)
        db.session.commit()
        
        flash(f'House {new_house.house_code} created successfully!', 'success')
        return redirect(url_for('create_house'))
    
    # Show joined house if user joined one, otherwise show created house
    is_creator = user_house is not None and user_house.created_by == player.id
    display_house = user_house if user_house else joined_house
    house_code = display_house.house_code if display_house else None

    house_players = []
    if display_house:
        house_players = HousePlayer.query.filter_by(house_id=display_house.id).join(Player).all()

    return render_template('create_house.html', 
                        user_house=user_house, 
                        joined_house=joined_house,
                        house_players=house_players,
                        username=user.username,
                        is_creator=is_creator,
                        house_code=display_house.house_code if display_house else None,)

@app.route('/delete_house/<int:house_id>', methods=['POST'])
def delete_house(house_id):
    """Delete house route"""
    if 'user_id' not in session or session.get('is_guest'):
        return redirect(url_for('auth.launch'))
    
    user_id = session.get('user_id')
    player = Player.query.filter_by(user_id=user_id).first()
    
    if not player:
        return redirect(url_for('auth.launch'))
    
    # Get house and verify ownership
    house = House.query.get(house_id)
    if not house or house.created_by != player.id:
        flash('House not found or you do not have permission to delete it.', 'error')
        return redirect(url_for('create_house'))
    
    # Delete house
    db.session.delete(house)
    db.session.commit()
    
    flash('House deleted successfully!', 'success')
    return redirect(url_for('create_house'))

@app.route('/join_house', methods=['GET', 'POST'])
def join_house():
    """Join house page - allows user to join a house by code"""
    if 'user_id' not in session or session.get('is_guest'):
        return redirect(url_for('auth.launch'))

    user_id = session.get('user_id')
    user = User.query.get(user_id)
    if not user:
        return redirect(url_for('auth.launch'))

    player = Player.query.filter_by(user_id=user_id).first()
    if not player:
        return redirect(url_for('auth.launch'))

    # 🟢 If the player is already in a house, skip join page
    existing_house_player = HousePlayer.query.filter_by(player_id=player.id).first()
    if existing_house_player:
        return redirect(url_for('create_house'))

    # 🟢 Normal join form flow continues below
    joined_house_code = None
    error_message = None

    if request.method == 'POST':
        house_code = request.form.get('house_code', '').strip().upper()

        if not house_code:
            flash('Please enter a house code', 'error')
            return redirect(url_for('join_house'))

        # Find house by code
        house = House.query.filter_by(house_code=house_code).first()

        if not house:
            flash('House not found. Please check the code.', 'error')
            return redirect(url_for('join_house'))

        # Check if user already created this house
        if house.created_by == player.id:
            flash('You cannot join your own house.', 'error')
            return redirect(url_for('join_house'))

        # Check if user is already in this house
        existing_participation = HousePlayer.query.filter_by(house_id=house.id, player_id=player.id).first()
        if existing_participation:
            flash('You are already in this house.', 'error')
            return redirect(url_for('create_house'))  # already a member -> go back to create_house view

        # Check if house is full
        if house.current_players >= house.max_players:
            flash('House is full. Cannot join.', 'error')
            return redirect(url_for('join_house'))

        # Check if house is in waiting status
        if house.status != 'waiting':
            flash('House is not accepting new players.', 'error')
            return redirect(url_for('join_house'))

        # Add player to house
        house_player = HousePlayer(
            house_id=house.id,
            player_id=player.id,
            is_ready=False
        )


        db.session.add(house_player)
        house.current_players = (house.current_players or 0) + 1
        db.session.commit()

        # Emit real-time notification to everyone in the house room
        try:
            room_name = f"house_{house.id}"
            payload = {
                "house_id": house.id,
                "player_id": player.id,
                # include a display name if available (adjust attribute path as needed)
                "player_name": getattr(player, "user").username if getattr(player, "user", None) else None,
                "current_players": house.current_players
            }
            socketio.emit('player_joined', payload, room=room_name)
        except Exception:
            app.logger.exception("emit player_joined failed")

        flash(f'Successfully joined house {house.name}!', 'success')
        return redirect(url_for('create_house'))


        # At this point the join succeeded. You can either:
        # 1) Redirect the user to the "create_house" page (which shows waiting UI)
        #    and let that page include the socket/polling logic; OR
        # 2) Render the join_house template with the joined_house_code embedded.
        #
        # I recommend redirecting to create_house for consistency:
        flash(f'Successfully joined house {house.name}!', 'success')
        return redirect(url_for('create_house'))

    # GET request: simply show the join form (joined_house_code stays None)
    return render_template('join_house.html', joined_house_code=joined_house_code, error=error_message)


@app.route('/exit_game', methods=['POST'])
def exit_game():
    """Called when a player clicks Exit Game from inside an in-progress/waiting game.
    Removes the player from the house, updates counts and status, and notifies sockets.
    """
    if 'user_id' not in session or session.get('is_guest'):
        return jsonify({"error": "not authenticated"}), 403

    user_id = int(session.get('user_id'))
    player = Player.query.filter_by(user_id=user_id).first()
    if not player:
        return jsonify({"error": "player not found"}), 404

    # Find the house the player is currently in (via HousePlayer)
    hp = HousePlayer.query.filter_by(player_id=player.id).first()
    if not hp:
        # Not in a house — just redirect back to create_house
        return jsonify({"ok": True, "redirect": url_for('create_house')})

    house = House.query.get(hp.house_id)
    if not house:
        # House missing — remove membership record for safety
        db.session.delete(hp)
        db.session.commit()
        return jsonify({"ok": True, "redirect": url_for('create_house')})

    try:
        # If the leaving player is the creator, choose a policy:
        # Option A (simple): cancel the in-progress game and set status back to 'waiting'
        # Option B (advanced): transfer ownership to another player (first one found)
        creator_left = (house.created_by == player.id)

        # Remove membership row
        db.session.delete(hp)
        # Decrement current_players safely
        house.current_players = max(0, (house.current_players or 1) - 1)

        if creator_left:
            # Try to transfer ownership to another player if any remain
            other_hp = HousePlayer.query.filter_by(house_id=house.id).first()
            if other_hp:
                # transfer created_by to that player's id (make them new creator)
                house.created_by = other_hp.player_id
                # Consider leaving status as 'waiting' unless you want to keep in_progress
                house.status = 'waiting'
                house.started_at = None
            else:
                # no other players — reset house to waiting (or optionally delete)
                house.status = 'waiting'
                house.started_at = None

        else:
            # Non-creator left: if no players remain, reset status
            if house.current_players <= 0:
                house.status = 'waiting'
                house.started_at = None

        db.session.commit()

        # Notify via sockets: everyone in the house should know someone left or game canceled
        room_name = f"house_{house.id}"
        # notify remaining players that someone left
        try:
            socketio.emit('player_left', {"player_id": player.id, "current_players": house.current_players}, room=room_name)
            # if creator left and we canceled or transferred, notify clients to stop/return to waiting
            if creator_left:
                socketio.emit('game_cancelled', {"reason": "creator_left", "house_id": house.id}, room=room_name)
        except Exception as e:
            app.logger.exception("socket emit error on exit_game")

        return jsonify({"ok": True, "redirect": url_for('create_house')})
    except Exception as e:
        app.logger.exception("Error in exit_game")
        db.session.rollback()
        return jsonify({"error": "internal error"}), 500

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)

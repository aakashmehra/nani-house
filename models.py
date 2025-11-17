# Database models for Battle Lanes (PostgreSQL)
# Includes authentication (login/signup) and inventory models

from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime
from sqlalchemy import update, func
from sqlalchemy.exc import SQLAlchemyError
from flask import Blueprint, request, jsonify, session
from contextlib import nullcontext
import traceback


# Initialize SQLAlchemy and Bcrypt - will be bound to app in init_db
db = SQLAlchemy()
bcrypt = Bcrypt()

# ============================================================================
# AUTHENTICATION MODELS (Login/Signup)
# ============================================================================
# helper to resolve user identifier (int id, username, or email) -> numeric users.id
def _resolve_user_id(user_identifier):
    """
    Accepts:
      - int (assumed to be users.id)
      - str (username or email)
    Returns users.id (int) or None if not found / invalid.
    """
    # already an int-like value
    try:
        if isinstance(user_identifier, int):
            return int(user_identifier)
        # strings that are digits are allowed (e.g. "123")
        if isinstance(user_identifier, str) and user_identifier.isdigit():
            return int(user_identifier)
    except (ValueError, TypeError):
        pass

    # otherwise treat as username or email
    if isinstance(user_identifier, str):
        u = db.session.query(User).filter((User.username == user_identifier) | (User.email == user_identifier)).first()
        return u.id if u else None

    return None

class User(db.Model):
    """User authentication model for login and signup"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    friends = db.Column(db.Text, nullable=True)  # Comma-separated list of friend user IDs: "1, 3, 5, 2, 6"
    
    # Relationships
    player = db.relationship('Player', backref='user', uselist=False, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        """Check if provided password matches hash"""
        return bcrypt.check_password_hash(self.password_hash, password)
    
    def get_friends_list(self):
        """Get list of friend user IDs as integers"""
        if not self.friends:
            return []
        return [int(fid.strip()) for fid in self.friends.split(',') if fid.strip().isdigit()]
    
    def add_friend(self, friend_id):
        """Add a friend ID to the friends list"""
        friends_list = self.get_friends_list()
        friend_id = int(friend_id)
        if friend_id not in friends_list:
            friends_list.append(friend_id)
            self.friends = ', '.join(map(str, friends_list))
            return True
        return False
    
    def remove_friend(self, friend_id):
        """Remove a friend ID from the friends list"""
        friends_list = self.get_friends_list()
        friend_id = int(friend_id)
        if friend_id in friends_list:
            friends_list.remove(friend_id)
            self.friends = ', '.join(map(str, friends_list)) if friends_list else None
            return True
        return False
    
    def __repr__(self):
        return f'<User {self.username}>'

class FriendRequest(db.Model):
    """Friend request model for tracking pending friend requests"""
    __tablename__ = 'friend_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    from_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    to_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, accepted, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    from_user = db.relationship('User', foreign_keys=[from_user_id], backref='sent_requests')
    to_user = db.relationship('User', foreign_keys=[to_user_id], backref='received_requests')
    
    def __repr__(self):
        return f'<FriendRequest {self.from_user_id} -> {self.to_user_id}>'

class Session(db.Model):
    """User session management"""
    __tablename__ = 'sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    session_token = db.Column(db.String(255), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    
    user = db.relationship('User', backref='sessions')
    
    def __repr__(self):
        return f'<Session {self.session_token[:10]}...>'

# ============================================================================
# PLAYER MODELS (Profile & Inventory)
# ============================================================================

class Player(db.Model):
    """Player profile and game data"""
    __tablename__ = 'players'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False, index=True)
    coins = db.Column(db.Integer, default=100, nullable=False)
    favorite_character = db.Column(db.String(50), nullable=True)
    wins = db.Column(db.Integer, default=0, nullable=False)
    losses = db.Column(db.Integer, default=0, nullable=False)
    total_games = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    equipped_character = db.Column(db.Integer, default=1, nullable=False)
    
    # Relationships
    characters = db.relationship('PlayerCharacter', backref='player', lazy=True, cascade='all, delete-orphan')
    dice = db.relationship('PlayerDice', backref='player', lazy=True, cascade='all, delete-orphan')
    chests = db.relationship('PlayerChest', backref='player', lazy=True, cascade='all, delete-orphan')
    houses = db.relationship('House', backref='created_by_player', lazy=True)
    
    @property
    def username(self):
        """Get the username from the associated User"""
        return self.user.username if self.user else None
    
    def __repr__(self):
        return f'<Player {self.username or self.user_id}>'

    def set_equipped_character(self, character_id: int) -> bool:
        """Set the equipped character for this player if they own it."""
        if self.id is None:
            return False
        owned = PlayerCharacter.query.filter_by(
            player_id=self.id,
            character_id=character_id
        ).first()
        if not owned:
            return False
        self.equipped_character = character_id
        return True
    
    @classmethod
    def get_coins(cls, user_id: int) -> int | None:
        """Return coin balance or None if player not found."""
        p = cls.query.filter_by(user_id=user_id).first()
        return p.coins if p else None

    @classmethod
    def change_coins(cls, user_id: int, delta: int, allow_negative: bool = True) -> dict:
        """
        Atomically add (delta>0) or subtract (delta<0) coins.

        Returns:
            {"success": bool, "coins": int|None, "error": None|string}
        Errors: "player_not_found", "insufficient_coins", or DB error string.
        """
        if delta == 0:
            current = cls.get_coins(user_id)
            return {"success": True, "coins": current, "error": None}

        try:
            # use the session transaction for atomicity
            ctx = db.session.begin() if not db.session.in_transaction() else nullcontext()
            with ctx:
                if allow_negative:
                    stmt = (
                        update(cls)
                        .where(cls.user_id == user_id)
                        .values(coins=cls.coins + delta, updated_at=func.now())
                        .returning(cls.coins)
                    )
                else:
                    stmt = (
                        update(cls)
                        .where(cls.user_id == user_id)
                        .where((cls.coins + delta) >= 0)
                        .values(coins=cls.coins + delta, updated_at=func.now())
                        .returning(cls.coins)
                    )

                res = db.session.execute(stmt)
                new_balance = res.scalar_one_or_none()

                if new_balance is None:
                    # check existence to give better error
                    exists = db.session.query(cls.id).filter_by(user_id=user_id).first()
                    if not exists:
                        return {"success": False, "coins": None, "error": "player_not_found"}
                    return {"success": False, "coins": None, "error": "insufficient_coins"}

                # commit happens automatically at context exit
                return {"success": True, "coins": int(new_balance), "error": None}

        except SQLAlchemyError as e:
            db.session.rollback()
            return {"success": False, "coins": None, "error": str(e)}

    @classmethod
    def set_coins(cls, user_id: int, amount: int) -> dict:
        """Force-set coins (no negative allowed)."""
        if amount < 0:
            return {"success": False, "coins": None, "error": "negative_amount_not_allowed"}
        try:
            ctx = db.session.begin() if not db.session.in_transaction() else nullcontext()
            with ctx:
                stmt = (
                    update(cls)
                    .where(cls.user_id == user_id)
                    .values(coins=amount, updated_at=func.now())
                    .returning(cls.coins)
                )
                res = db.session.execute(stmt)
                new_balance = res.scalar_one_or_none()
                if new_balance is None:
                    return {"success": False, "coins": None, "error": "player_not_found"}
                return {"success": True, "coins": int(new_balance), "error": None}
        except SQLAlchemyError as e:
            db.session.rollback()
            return {"success": False, "coins": None, "error": str(e)}

    @classmethod
    def transfer_coins(cls, from_user_id: int | str, to_user_id: int | str, amount: int) -> dict:
        if amount <= 0:
            return {"success": False, "error": "amount_must_be_positive"}

        from_uid = _resolve_user_id(from_user_id)
        to_uid = _resolve_user_id(to_user_id)
        if from_uid is None or to_uid is None:
            return {"success": False, "error": "sender_or_recipient_not_found"}

        try:
            with db.session.begin_nested():
                stmt_sub = (
                    update(cls)
                    .where(cls.user_id == from_uid)
                    .where((cls.coins - amount) >= 0)
                    .values(coins=cls.coins - amount, updated_at=func.now())
                    .returning(cls.coins)
                )
                from_new = db.session.execute(stmt_sub).scalar_one_or_none()
                if from_new is None:
                    return {"success": False, "error": "insufficient_funds_or_sender_not_found"}

                stmt_add = (
                    update(cls)
                    .where(cls.user_id == to_uid)
                    .values(coins=cls.coins + amount, updated_at=func.now())
                    .returning(cls.coins)
                )
                to_new = db.session.execute(stmt_add).scalar_one_or_none()
                if to_new is None:
                    raise ValueError("recipient_not_found")

                return {"success": True, "from_coins": int(from_new), "to_coins": int(to_new)}

        except ValueError as ve:
            db.session.rollback()
            return {"success": False, "error": str(ve)}
        except SQLAlchemyError as e:
            db.session.rollback()
            return {"success": False, "error": str(e)}


# ============================================================================
# INVENTORY MODELS (Characters, Dice, Chests)
# ============================================================================

class Character(db.Model):
    """Character definitions"""
    __tablename__ = 'characters'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    character_type = db.Column(db.String(50), nullable=False)  # Support, Fighter, etc.
    ability = db.Column(db.String(200), nullable=False)
    range_value = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=True)
    image_path = db.Column(db.String(255), nullable=True)
    price = db.Column(db.Integer, nullable=True)  # Price in coins
    total_matches_played = db.Column(db.Integer, default=0, nullable=False)  # Total matches played with this character
    
    def __repr__(self):
        return f'<Character {self.name}>'

class PlayerCharacter(db.Model):
    """Player's character inventory"""
    __tablename__ = 'player_characters'
    
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False, index=True)
    character_id = db.Column(db.Integer, db.ForeignKey('characters.id'), nullable=False)
    unlocked = db.Column(db.Boolean, default=False, nullable=False)
    obtained_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    character = db.relationship('Character', backref='player_ownerships')
    
    def __repr__(self):
        return f'<PlayerCharacter {self.player_id} - {self.character_id}>'

class Dice(db.Model):
    """Dice definitions"""
    __tablename__ = 'dice'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    effect = db.Column(db.String(200), nullable=False)
    rarity = db.Column(db.String(20), nullable=False)  # Common, Rare, Epic, Legendary
    image_path = db.Column(db.String(255), nullable=True)
    price = db.Column(db.Integer, nullable=True)  # Price in coins
    
    def __repr__(self):
        return f'<Dice {self.name}>'

class PlayerDice(db.Model):
    """Player's dice inventory"""
    __tablename__ = 'player_dice'
    
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False, index=True)
    dice_id = db.Column(db.Integer, db.ForeignKey('dice.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    obtained_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    dice = db.relationship('Dice', backref='player_ownerships')
    
    def __repr__(self):
        return f'<PlayerDice {self.player_id} - {self.dice_id}>'

class Chest(db.Model):
    """Chest/Shop item definitions"""
    __tablename__ = 'chests'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    chest_type = db.Column(db.String(50), nullable=False)  # Ability Pack, Character Pack, etc.
    price = db.Column(db.Integer, nullable=True)  # Price in coins
    description = db.Column(db.Text, nullable=True)
    image_path = db.Column(db.String(255), nullable=True)
    
    def __repr__(self):
        return f'<Chest {self.name}>'

class PlayerChest(db.Model):
    """Player's chest inventory"""
    __tablename__ = 'player_chests'
    
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False, index=True)
    chest_id = db.Column(db.Integer, db.ForeignKey('chests.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    obtained_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    chest = db.relationship('Chest', backref='player_ownerships')
    
    def __repr__(self):
        return f'<PlayerChest {self.player_id} - {self.chest_id}>'

# ============================================================================
# SHOP MODELS
# ============================================================================

class Shop(db.Model):
    """Shop items for purchase"""
    __tablename__ = 'shop'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    item_type = db.Column(db.String(50), nullable=False)  # Character Pack, Dice Pack, Ability Pack, etc.
    cost = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=True)
    image_path = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Shop {self.name}>'

# ============================================================================
# GAME MODELS (Houses, Games)
# ============================================================================

class House(db.Model):
    """Game house for multiplayer matches"""
    __tablename__ = 'houses'
    
    id = db.Column(db.Integer, primary_key=True)
    house_code = db.Column(db.String(10), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)
    max_players = db.Column(db.Integer, default=6, nullable=False)
    current_players = db.Column(db.Integer, default=0, nullable=False)
    status = db.Column(db.String(20), default='waiting', nullable=False)  # waiting, in_progress, finished
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime, nullable=True)
    finished_at = db.Column(db.DateTime, nullable=True)
    
    players = db.relationship('HousePlayer', backref='house', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<House {self.house_code}>'

class HousePlayer(db.Model):
    """Players in a game house"""
    __tablename__ = 'house_players'
    
    id = db.Column(db.Integer, primary_key=True)
    house_id = db.Column(db.Integer, db.ForeignKey('houses.id'), nullable=False, index=True)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False, index=True)
    character_id = db.Column(db.Integer, db.ForeignKey('characters.id'), nullable=True)
    position = db.Column(db.Integer, nullable=True)  # Player position in house
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_ready = db.Column(db.Boolean, default=False, nullable=False)
    
    player = db.relationship('Player', backref='house_participations')
    character = db.relationship('Character', backref='house_players')
    
    def __repr__(self):
        return f'<HousePlayer {self.house_id} - {self.player_id}>'

class Game(db.Model):
    """Individual game/match record"""
    __tablename__ = 'games'
    
    id = db.Column(db.Integer, primary_key=True)
    house_id = db.Column(db.Integer, db.ForeignKey('houses.id'), nullable=False, index=True)
    winner_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=True)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    finished_at = db.Column(db.DateTime, nullable=True)
    game_data = db.Column(db.JSON, nullable=True)  # Store game state/log
    
    house = db.relationship('House', backref='games')
    winner = db.relationship('Player', backref='won_games')
    
    def __repr__(self):
        return f'<Game {self.id}>'

# ============================================================================
# DATABASE INITIALIZATION
# ============================================================================

def init_db(app):
    """Initialize the database with the Flask app"""
    db.init_app(app)
    bcrypt.init_app(app)
    
    with app.app_context():
        db.create_all()
        
        # # Initialize default characters if they don't exist
        # if Character.query.count() == 0:
        #     default_characters = [
        #         Character(name='Ditte', character_type='Support', ability='Heals nearby teammates (20%/turn)', range_value='1 zone', description='Calm, wise, healer monk'),
        #         Character(name='Tontar', character_type='Fighter', ability='Double punch (2 hits per move)', range_value='Close', description='Hot-headed brawler'),
        #         Character(name='Makdi', character_type='Trap Setter', ability='Slows enemies with webs', range_value='1-2 zones', description='Sneaky and quiet'),
        #         Character(name='Mishu', character_type='Speedster', ability='Moves twice per turn', range_value='2 zones', description='Fast and playful'),
        #         Character(name='Dholky', character_type='Tank', ability='Reduces damage 50% for 1 turn', range_value='Close', description='Funny, tough drummer'),
        #         Character(name='Beaster', character_type='Berserker', ability='Gets stronger each time hit (+10% dmg)', range_value='1 zone', description='Wild and angry'),
        #         Character(name='Prepto', character_type='Teleporter', ability='Jump to any lane once per game', range_value='Any zone', description='Mysterious wizard'),
        #         Character(name='Ishada', character_type='Sniper', ability='Shoots 5 zones away (one-shot chance)', range_value='Long', description='Silent assassin'),
        #         Character(name='Padupie', character_type='Bomber', ability='Missiles hit 3 zones at once', range_value='Mid-range', description='Crazy explosive expert'),
        #     ]
        #     for char in default_characters:
        #         db.session.add(char)
        
        # # Initialize default dice if they don't exist
        # if Dice.query.count() == 0:
        #     default_dice = [
        #         Dice(name='Fortune Core', effect='Normal defense dice', rarity='Common'),
        #         Dice(name='Risk Roller', effect='Cursed dice (can defend or backfire)', rarity='Rare'),
        #         Dice(name='Blaze Cube', effect='Boosts attack next turn', rarity='Epic'),
        #         Dice(name='Frost Prism', effect='Slows attacker', rarity='Legendary'),
        #     ]
        #     for dice in default_dice:
        #         db.session.add(dice)
        
        # # Initialize default chests if they don't exist
        # if Chest.query.count() == 0:
        #     default_chest_items = [
        #         Chest(name='Ability Pack', chest_type='Ability Pack', cost=50, description='Random new weapons or powers'),
        #         Chest(name='Character Pack', chest_type='Character Pack', cost=100, description='Unlocks new fighters'),
        #         Chest(name='Power Dice Pack', chest_type='Power Dice', cost=75, description='Extra or stronger dice'),
        #         Chest(name='Cursed Dice Pack', chest_type='Cursed Dice', cost=150, description='Risky but powerful'),
        #     ]
        #     for chest_item in default_chest_items:
        #         db.session.add(chest_item)
        
        # # Initialize default shop items if they don't exist
        # if Shop.query.count() == 0:
        #     default_shop_items = [
        #         Shop(name='Ability Pack', item_type='Ability Pack', cost=50, description='Random new weapons or powers', is_active=True),
        #         Shop(name='Character Pack', item_type='Character Pack', cost=100, description='Unlocks new fighters', is_active=True),
        #         Shop(name='Power Dice Pack', item_type='Power Dice', cost=75, description='Extra or stronger dice', is_active=True),
        #         Shop(name='Cursed Dice Pack', item_type='Cursed Dice', cost=150, description='Risky but powerful', is_active=True),
        #         Shop(name='Character Unlock', item_type='Character', cost=200, description='Unlock a random character', is_active=True),
        #         Shop(name='Dice Bundle', item_type='Dice', cost=120, description='Bundle of 3 random dice', is_active=True),
        #     ]
        #     for shop_item in default_shop_items:
        #         db.session.add(shop_item)
        
        db.session.commit()



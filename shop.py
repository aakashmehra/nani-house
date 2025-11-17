from sqlalchemy import func
from flask import Blueprint, request, jsonify, session
from contextlib import nullcontext
from models import Player, Shop, Chest, PlayerChest, Dice, PlayerDice, Character, PlayerCharacter
import traceback
from models import db


shop_bp = Blueprint('shop', __name__)

def _session_in_transaction(session):
    if hasattr(session, "in_transaction"):
        try:
            return bool(session.in_transaction())
        except Exception:
            pass
    return getattr(session, "transaction", None) is not None

@shop_bp.route('/buy', methods=['POST'])
def buy_item():
    print("=== BUY: ENTRY ===")
    try:
        print("DB URL:", db.engine.url)
    except Exception:
        pass
    print("session object type:", type(db.session))
    print("session.transaction attribute:", getattr(db.session, "transaction", None))
    print("session in_transaction (helper):", _session_in_transaction(db.session))

    if 'user_id' not in session:
        return jsonify(success=False, error='not_authenticated'), 401

    user_id = session['user_id']
    data = request.get_json(silent=True) or {}
    item_id = data.get('item_id')
    if not item_id:
        return jsonify(success=False, error='missing_item_id'), 400

    try:
        shop_item = Shop.query.get(item_id)
        if not shop_item or not shop_item.is_active:
            return jsonify(success=False, error='item_not_found_or_inactive'), 404

        cost = int(shop_item.cost)

        # --- transaction selection (safe for scoped_session) ---
        already_in_tx = _session_in_transaction(db.session)
        print("=== BUY: before transaction context ===")
        print("already_in_tx:", already_in_tx)

        if already_in_tx:
            ctx = db.session.begin_nested()   # savepoint
            started_top_level = False
            print("Using begin_nested() (savepoint)")
        else:
            ctx = nullcontext()               # don't call begin(); we'll commit manually
            started_top_level = True
            print("No existing transaction — using nullcontext(), will commit after flush")

        with ctx:
            # --- inside transaction context ---
            print("=== BUY: INSIDE TRANSACTION CONTEXT ===")
            print("session.transaction (inside):", getattr(db.session, "transaction", None))
            print("session in_transaction (helper inside):", _session_in_transaction(db.session))
            print("SESSION NEW (before ops):", list(db.session.new))
            print("SESSION DIRTY (before ops):", list(db.session.dirty))

            player = db.session.query(Player).filter_by(user_id=user_id).with_for_update().first()
            if not player:
                print("Player not found")
                return jsonify(success=False, error='player_not_found'), 404

            if player.coins < cost:
                print("Insufficient coins:", player.coins, "cost:", cost)
                return jsonify(success=False, error='insufficient_coins', coins=player.coins), 400

            player.coins = player.coins - cost
            player.updated_at = func.now()

            added = None
            itype = (shop_item.item_type or '').strip().lower()
            
            print(f"DEBUG: Processing purchase - shop_item.name='{shop_item.name}', item_type='{shop_item.item_type}', itype='{itype}'")

            # Handle different item types based on shop database item_type
            if itype == 'chest':
                print(f"DEBUG: Item type is 'chest', looking for chest with name '{shop_item.name}'")
                # Find the specific chest by name - must match exactly
                chosen_chest = Chest.query.filter(func.lower(Chest.name) == func.lower(shop_item.name)).first()
                if not chosen_chest:
                    print(f"ERROR: Chest not found for shop item '{shop_item.name}' (item_type: {shop_item.item_type})")
                    print(f"Available chests: {[c.name for c in Chest.query.all()]}")
                    raise ValueError(f'chest_not_found: No chest found matching "{shop_item.name}"')
                print(f"DEBUG: Found chest '{chosen_chest.name}' (id: {chosen_chest.id}), adding to PlayerChest")
                # Add or update player chest inventory
                pc = PlayerChest.query.filter_by(player_id=player.id, chest_id=chosen_chest.id).first()
                if pc:
                    pc.quantity += 1
                    pc.obtained_at = func.now()
                    print(f"DEBUG: Updated existing PlayerChest, new quantity: {pc.quantity}")
                else:
                    new_pc = PlayerChest(player_id=player.id, chest_id=chosen_chest.id, quantity=1)
                    db.session.add(new_pc)
                    print(f"DEBUG: Created new PlayerChest for chest '{chosen_chest.name}'")
                added = {'type': 'chest', 'chest_id': chosen_chest.id, 'chest_name': chosen_chest.name, 'quantity_added': 1}
                
            elif itype == 'dice':
                # Find matching dice by name, or get random dice
                chosen_dice = Dice.query.filter(func.lower(Dice.name) == func.lower(shop_item.name)).first()
                if not chosen_dice:
                    chosen_dice = Dice.query.order_by(func.random()).first()
                if not chosen_dice:
                    raise ValueError('no_dice_available')
                # Add or update player dice inventory
                pd = PlayerDice.query.filter_by(player_id=player.id, dice_id=chosen_dice.id).first()
                if pd:
                    pd.quantity += 1
                    pd.obtained_at = func.now()
                else:
                    db.session.add(PlayerDice(player_id=player.id, dice_id=chosen_dice.id, quantity=1))
                added = {'type': 'dice', 'dice_id': chosen_dice.id, 'dice_name': chosen_dice.name, 'quantity_added': 1}
                
            elif itype == 'character':
                # Find matching character by name, or get random character
                chosen_character = Character.query.filter(func.lower(Character.name) == func.lower(shop_item.name)).first()
                if not chosen_character:
                    chosen_character = Character.query.order_by(func.random()).first()
                if not chosen_character:
                    raise ValueError('no_characters_available')
                # Check if player already owns this character
                existing = PlayerCharacter.query.filter_by(player_id=player.id, character_id=chosen_character.id).first()
                if existing:
                    print("Player already owns character:", chosen_character.id)
                    return jsonify(success=False, error='already_owned_character', character_id=chosen_character.id), 400
                # Add character to player inventory
                db.session.add(PlayerCharacter(player_id=player.id, character_id=chosen_character.id, unlocked=True))
                added = {'type': 'character', 'character_id': chosen_character.id, 'character_name': chosen_character.name}
            else:
                print("Unsupported item_type:", shop_item.item_type)
                return jsonify(success=False, error='unsupported_item_type', item_type=shop_item.item_type), 400

            print("About to flush session...")
            db.session.flush()

            print("=== BUY: AFTER FLUSH ===")
            print("SESSION NEW (after flush):", list(db.session.new))
            print("SESSION DIRTY (after flush):", list(db.session.dirty))
            print("transaction active (after flush):", _session_in_transaction(db.session))

            # Commit if we were the top-level (we didn't open a transaction)
            if started_top_level:
                try:
                    db.session.commit()
                    print("Committed session (started_top_level=True)")
                except Exception as e:
                    print("Commit failed:", e)
                    db.session.rollback()
                    raise

            return jsonify(success=True, coins=player.coins, added=added)

    except Exception as e:
        print("=== BUY: EXCEPTION ===")
        traceback.print_exc()
        try:
            print("session.transaction (on exception):", getattr(db.session, "transaction", None))
            print("session in_transaction (helper on exception):", _session_in_transaction(db.session))
            print("SESSION NEW (on exception):", list(db.session.new))
            print("SESSION DIRTY (on exception):", list(db.session.dirty))
        except Exception:
            pass

        try:
            db.session.rollback()
        except Exception:
            print("rollback failed")
        return jsonify(success=False, error='unexpected_error', detail=str(e)), 500
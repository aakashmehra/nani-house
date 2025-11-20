import json, datetime, random
from models import House, HousePlayer, Player, User, db
from classes.characters import Ditte, Tontar, Makdi, Mishu, Dholky, Beaster, Prepto, Ishada, Padupie

characters = {
    1: Ditte(),
    2: Tontar(),
    3: Makdi(),
    4: Mishu(),
    5: Dholky(),
    6: Beaster(),
    7: Prepto(),
    8: Ishada(),
    9: Padupie(),
}

def create_file(path, user_id, match_id):
    data = {
        "match_id" : match_id,
        "satrted_at" : datetime.datetime.utcnow().isoformat()
    }
    house = db.session.query(House.id).filter_by(created_by=user_id).first()
    players = db.session.query(HousePlayer.player_id).filter_by(house_id=house[0]).all()
    
    data["players"] = {}
    i = 0
    for player in players:
        chosen_character = characters[db.session.query(Player.equipped_character).filter_by(user_id=player[0]).first()[0]]
        user = db.session.query(User.username).filter_by(id=player[0]).first()
        data["players"][player[0]] = {}
        data["players"][player[0]]["user"] = user[0]
        data["players"][player[0]]["id"] = chosen_character.id
        data["players"][player[0]]["name"] = chosen_character.name
        data["players"][player[0]]["max_health"] = chosen_character.health
        data["players"][player[0]]["health"] = chosen_character.health
        data["players"][player[0]]["shield"] = chosen_character.shield
        data["players"][player[0]]["dice_id"] = 1
        data["players"][player[0]]["position"] = [0,0]
        i += 1

    data["player_count"] = i
    print(data)

    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def read_json(path):
    with open(path, "r") as f:
        return json.load(f)

def add_pos(path, user_id, pos):
    data = read_json(path)
    
    data["players"][str(user_id)]["position"] = pos

    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def gen_turn_order(path):
    with open(path, "r") as f:
        data =  json.load(f)

    turn = []
    for player in data["players"]:
        turn.append(player)

    random.shuffle(turn)
    data["turn_order"] = turn
    data["current_turn_index"] = 0
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

    return turn

def modify_json(path, el_to_modify, new_val):
    data = read_json(path)
    
    obj = data
    for key in el_to_modify[:-1]:
        obj = obj[key]

    obj[el_to_modify[-1]] = new_val

    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def create_board(path):
    board_cells =  []

    for i in range(10):
        row = []
        for j in range(10):
            cell = random.randint(0, 3)
            row.append(cell)
        board_cells.append(row)
        
    print(board_cells)
    modify_json(path, ["board_layout"], board_cells)

    return board_cells
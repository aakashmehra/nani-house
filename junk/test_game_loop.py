from classes.characters import Tontar, Ditte, Makdi, Prepto, Padupie
from classes.dice import FortuneCore
import random


player_count = input("Enter number of players (2-4): ")
players = []
for i in range(int(player_count)):
    name = input(f"Enter name for Player {i+1}: ")
    character_choice = input(f"Choose character for {name} (1: Ditte, 2: Tontar, 3: Makdi, 4: Prepto, 5: Padupie): ")
    if character_choice == '1':
        character = Ditte()
    elif character_choice == '2':
        character = Tontar()
    elif character_choice == '3':
        character = Makdi()
    elif character_choice == '4':
        character = Prepto()
    elif character_choice == '5':
        character = Padupie()
    else:
        print("Invalid choice, defaulting to Ditte.")
        character = Ditte()
    
    player_data = {"name": name, "character": character, "dice": FortuneCore()}
    players.append(player_data)

game_board = []
for i in range(10):
    new_list = []
    for i in range(10):
        new_list.append([])
    game_board.append(new_list)

current_pos = {}

for player in players:
    x = random.randint(0, 9)
    y = random.randint(0, 9)
    game_board[x][y] = player["name"]
    current_pos[player["name"]] = (x, y)

def print_board(game_board):
    for row in game_board:
        for cell in row:
            if cell:
                print(cell, end="\t")
            else: 
                print("__", end="\t")
        print()



def menu():
    print("1. Move")
    print("2. Attack")
    print("3. Special Ability")
    print("4. End Turn")
    choice = input("Choose an action: ")
    return choice

print_board(game_board)

turn = 0
while True:
    if turn >= len(players):
        turn = 0
    print("It's", players[turn]["name"]+"'s turn!")
    choice = menu()
    while choice != '4':
        choices = []
        if 1 not in choices and choice == '1':
            print("Move selected")
            roll = players[turn]["dice"].roll()
            print(f"You rolled a {roll}")
            x,y = current_pos[players[turn]["name"]]
            game_board[x][y] = []
            if y + roll < 10:
                y += roll
                game_board[x][y] = players[turn]["name"]
                current_pos[players[turn]["name"]] = (x,y)
            else:
                possibe_moves = 9 - y
                y += possibe_moves
                x += roll - possibe_moves
                game_board[x][y] = players[turn]["name"]
                current_pos[players[turn]["name"]] = (x,y)
            print_board(game_board)
            choices.append(1)
        elif choice == '2' and 2 not in choices:
            print("Attack selected")
            attacker = players[turn]["character"]
            attacker.attack_target(players[turn]["character"])
            choices.append(2)
        elif choice == '3' and 3 not in choices:
            print("Special Ability selected")
            # Implement special ability logic here
            choices.append(3)
        else:
            print("Invalid choice, try again.")
        choice = menu()
    turn += 1
    print(f"{players[turn-1]['name']}'s turn ended.")
    print_board(game_board)
    for player in players:
        if player["character"].health <= 0:
            print(f"{player['name']}'s character {player['character'].name} has been defeated!")
            players.remove(player)
    if len(players) == 1:
        print(f"{players[0]['name']} wins the game!")
        break

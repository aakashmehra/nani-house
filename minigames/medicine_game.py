import random

# 20 effects: mix of positive, negative, and neutral
effects = [+15, +15, +15, +15, +15, +15, +15, +15, +5, -5, -5, -5, -5, 0, 0, 0, 0 ,0 ,0, 0]
random.shuffle(effects)

medicines = {i+1: effects[i] for i in range(20)}

print("Choose 3 medicines (enter numbers 1–20):")

choices = []
total_hp = 0

for i in range(3):
    while True:
        try:
            choice = int(input(f"Pick medicine {i+1}: "))
            
            if choice not in medicines:
                print("Invalid number! Choose between 1–20.")
                continue

            if choice in choices:
                print("You already picked this one! Choose another.")
                continue

            # valid pick
            effect = medicines[choice]
            print(f" → Medicine {choice} gives HP: {effect}\n")
            choices.append(choice)
            total_hp += effect
            break

        except ValueError:
            print("Enter a valid number!")

print("===== FINAL RESULTS =====")
for c in choices:
    print(f"Medicine {c} → HP: {medicines[c]}")

print("-------------------------")
print(f"Total HP Change: {total_hp}")
print("=========================")

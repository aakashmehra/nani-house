from classes.dice import FortuneCore

class Characters:
    def __init__(self):
        self.id = 0
        self.name = "Character"
        self.type = "Normal"
        self.health = 100
        self.attack = 10
        self.shield = 0
        self.range = 1
        self.dice = FortuneCore()

    def is_alive(self):
        return self.health > 0
    
    def take_damage(self, damage):
        effective_damage = max(0, damage - (self.shield/100)*damage)
        self.health -= effective_damage
        self.shield = max(0, self.shield - (damage * 0.1))
        print(f"{self.name} takes {effective_damage} damage, health is now {self.health}")

    def attack_target(self, target):
        print(f"{self.name} attacks {target.name} for {self.attack} damage!")
        target.take_damage(self.attack)

    def heal(self, amount):
        self.health += amount
        print(f"{self.name} heals for {amount}, health is now {self.health}")

class Ditte(Characters):
    def __init__(self):
        super().__init__()
        self.id = 1
        self.name = "Ditte"
        self.type = "Support"
        self.health = 120
        self.attack = 15
        self.shield = 20
        self.range = [0,100]

    def special_ability(self):
        self.heal(20)
        print(f"{self.name} uses Healing Light!")


class Tontar(Characters):
    def __init__(self):
        super().__init__()
        self.id = 2
        self.name = "Tontar"
        self.type = "Fighter"
        self.health = 110
        self.attack = 20
        self.shield = 0
        self.range = [0,2]

    def special_ability(self, target):
        print(f"{self.name} uses Power Strike!")
        target.take_damage(self.attack * 1.5)


class Makdi(Characters):    
    def __init__(self):
        super().__init__()
        self.id = 3
        self.name = "Makdi"
        self.type = "Trapster"
        self.health = 100
        self.attack = 12
        self.shield = 3
        self.range = [1,100]

    def special_ability(self):
        print(f"{self.name} sets a trap!")


class Mishu(Characters):
    def __init__(self):
        super().__init__()
        self.id = 4
        self.name = "Mishu"
        self.type = "Speedster"
        self.health = 90
        self.attack = 15
        self.shield = 0
        self.range = [0,2]

    def special_ability(self):
        print(f"{self.name} uses Quick Dash!(Moves 2 spaces and damages enemy in path)")


class Dholky(Characters):
    def __init__(self):
        super().__init__()
        self.id = 5
        self.name = "Dholky"
        self.type = "Tank"
        self.health = 250
        self.attack = 8
        self.shield = 0
        self.range = [0,1]

    def special_ability(self):
        self.shield += 15
        print(f"{self.name} uses Fortify! Shield increased to {self.shield} for 2 rounds")

class Beaster(Characters):
    def __init__(self):
        super().__init__()
        self.id = 6
        self.name = "Beaster"
        self.type = "Berserker"
        self.health = 130
        self.attack = 18
        self.shield = 10
        self.range = [0,1]

    def special_ability(self):
        self.attack += 5
        print(f"{self.name} uses Rage! Attack increased to {self.attack} for 3 rounds")


class Prepto(Characters):
    def __init__(self):
        super().__init__()
        self.id = 7
        self.name = "Prepto"
        self.type = "Teleporter"
        self.health = 100
        self.attack = 12
        self.shield = 0
        self.range = [0, 100]

    def special_ability(self):
        print(f"{self.name} uses Teleport!")


class Ishada(Characters):
    def __init__(self):
        super().__init__()
        self.id = 8
        self.name = "Ishada"
        self.type = "Sniper"
        self.health = 95
        self.attack = 25
        self.shield = 0
        self.range = [10, 20]

    def special_ability(self):
        print(f"{self.name} uses Headshot!")


class Padupie(Characters):
    def __init__(self):
        super().__init__()
        self.id = 9
        self.name = "Padupie"
        self.type = "Bomber"
        self.health = 110
        self.attack = 22
        self.shield = 0
        self.range = [0,20]

    def special_ability(self):
        print(f"{self.name} uses Bomb Attack!")

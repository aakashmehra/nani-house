import random

class FortuneCore:
    def __init__(self, sides=6):
        self.sides = sides
        self.id = 1

    def roll(self):
        return random.randint(1, self.sides)

class RiskRoller(FortuneCore):
    def __init__(self, sides=3):
        super().__init__(sides)
        self.id = 2

class BlazeCube(FortuneCore):
    def __init__(self, sides=6):
        super().__init__(sides)
        self.id = 3

    def roll(self):
        print("Attack Boosted! for next attack")
        return super().roll()

class FrostPrism(FortuneCore):
    def __init__(self, sides=6):
        super().__init__(sides)
        self.id = 4

    def roll(self):
        print("Slow attack Enabled for next attack!")
        return super().roll()

class DoubleFortuneCore(FortuneCore):
    def __init__(self, sides=6):
        super().__init__(sides)
        self.id = 5

    def roll(self):
        n1 = super().roll()
        n2 = super().roll()
        print("Rolling first Dice:", n1)
        print("Rolling second Dice:", n2)
        return (n1 + n2)

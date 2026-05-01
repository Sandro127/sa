# Updated Bot.py Content

# Constants
STAGE = {
    'BATTLES': 0.00,
    'RISORSE_PER_BATTAGLIA': 0
}

# Simplified Dungeon Data Structure
class Dungeon:
    def __init__(self):
        self.st = 0.0  # Player strength as float
        self.rew = 0  # Resources accumulated

# Player commands
class Player:
    def __init__(self):
        self.dungeon = Dungeon()

    def strength_command(self, force):
        # Separate command for setting player force
        self.dungeon.st = force

    def update_logic(self, victory_count):
        # Updated logic for victories
        if victory_count == 1:
            self.dungeon.rew += 5
        elif victory_count == 2:
            self.dungeon.rew += 10

        # Update battle statistics
        STAGE['BATTLES'] += 0.01 * victory_count
        if STAGE['BATTLES'] >= 0.15:
            self.increment_stage()

    def increment_stage(self):
        # Increment the stage and reset battles
        STAGE['BATTLES'] = 0.00

    def display_stats(self):
        # Stats display
        total_resources = self.dungeon.st * self.dungeon.rew
        remaining_to_target = (TARGET - total_resources) if 'TARGET' in globals() else 0
        print(f'Current Stage Battles: {STAGE['BATTLES']},
              Resources per Battle: {STAGE['RISORSE_PER_BATTAGLIA']},
              Total Resources: {total_resources},
              Remaining to Target: {remaining_to_target}')
# game_manager.py
from typing import Tuple, Dict, List, Optional, Any
from threading import Lock
from classes.dice import FortuneCore
from classes.characters import Characters
import random

Position = Tuple[int, int]

class GameManager:
    def __init__(self, board_size: int = 10, allow_shared_tiles: bool = True):
        self.board_size = board_size
        # player_id -> Characters instance
        self.players: Dict[str, Characters] = {}
        # player_id -> (x,y)
        self.positions: Dict[str, Position] = {}
        # (x,y) -> set[player_id]  (fast occupancy check; supports shared tiles)
        self.occupancy: Dict[Position, set] = {}
        self.lock = Lock()
        # optional: store turn order
        self.turn_order: List[str] = []
        self.current_turn_index: int = 0

        # whether multiple players can share the same tile
        self.allow_shared_tiles = allow_shared_tiles

    # ---------------------
    # helpers
    # ---------------------
    def in_bounds(self, pos: Position) -> bool:
        x, y = pos
        return 0 <= x < self.board_size and 0 <= y < self.board_size

    def is_occupied(self, pos: Position) -> bool:
        """Returns True if occupancy set exists and non-empty."""
        return bool(self.occupancy.get(pos))

    def occupants(self, pos: Position) -> List[str]:
        return list(self.occupancy.get(pos, set()))

    def _add_occupant(self, pos: Position, player_id: str):
        s = self.occupancy.get(pos)
        if not s:
            s = set()
            self.occupancy[pos] = s
        s.add(player_id)

    def _remove_occupant(self, pos: Position, player_id: str):
        s = self.occupancy.get(pos)
        if not s:
            return
        s.discard(player_id)
        if not s:
            # remove empty set to keep is_occupied simple
            self.occupancy.pop(pos, None)

    def neighbors(self, pos: Position) -> List[Position]:
        x, y = pos
        cand = [(x+1,y),(x-1,y),(x,y+1),(x,y-1)]
        return [p for p in cand if self.in_bounds(p)]

    # Manhattan distance
    def manhattan(self, a: Position, b: Position) -> int:
        return abs(a[0]-b[0]) + abs(a[1]-b[1])

    # ---------------------
    # player / spawn / remove
    # ---------------------
    def spawn_player(self, player_id: str, char: Characters, pos: Optional[Position] = None) -> Position:
        """Add a player to the game, optionally at a position. If pos None, pick random free tile (or any if shared allowed)."""
        with self.lock:
            if player_id in self.players:
                raise ValueError("player already spawned")

            # pick a free or random cell if not provided
            if pos is None or not self.in_bounds(pos):
                free = [(x,y) for x in range(self.board_size) for y in range(self.board_size)]
                if not free:
                    raise RuntimeError("Board full")
                pos = random.choice(free)

            # if shared tiles aren't allowed, ensure not occupied
            if not self.allow_shared_tiles:
                # find an unoccupied tile if requested pos is taken
                if self.is_occupied(pos):
                    free_unocc = [(x,y) for x in range(self.board_size) for y in range(self.board_size) if not self.is_occupied((x,y))]
                    if not free_unocc:
                        raise RuntimeError("Board full (no free tiles)")
                    pos = random.choice(free_unocc)

            self.players[player_id] = char
            self.positions[player_id] = pos
            self._add_occupant(pos, player_id)
            self.turn_order.append(player_id)
            return pos

    def remove_player(self, player_id: str):
        with self.lock:
            if player_id not in self.players:
                return
            pos = self.positions.pop(player_id, None)
            if pos:
                self._remove_occupant(pos, player_id)
            self.players.pop(player_id, None)
            if player_id in self.turn_order:
                idx = self.turn_order.index(player_id)
                self.turn_order.remove(player_id)
                if idx <= self.current_turn_index and self.current_turn_index > 0:
                    self.current_turn_index -= 1
                self.current_turn_index %= max(1, len(self.turn_order)) if self.turn_order else 0

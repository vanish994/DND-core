"""Camada de jogo de dungeon, separada do Rule Engine e do Orquestrador."""

from .combat_board import BoardPosition, CombatBoard
from .generator import DungeonGenerator
from .models import DungeonFloor, DungeonRoom, DungeonRun, RoomKind, RunStatus

__all__ = [
    "BoardPosition",
    "CombatBoard",
    "DungeonGenerator",
    "DungeonFloor",
    "DungeonRoom",
    "DungeonRun",
    "RoomKind",
    "RunStatus",
]

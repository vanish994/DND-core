"""Modelos de domínio do crawler; sem regras de D&D ou dependência de UI."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RoomKind(StrEnum):
    START = "start"
    COMBAT = "combat"
    TREASURE = "treasure"
    EVENT = "event"
    BOSS = "boss"
    STAIRS = "stairs"


class RunStatus(StrEnum):
    ACTIVE = "active"
    DEFEATED = "defeated"
    COMPLETED = "completed"


@dataclass(frozen=True, slots=True)
class DungeonRoom:
    id: str
    kind: RoomKind
    x: int
    y: int
    width: int
    height: int
    connections: tuple[str, ...] = ()

    @property
    def center(self) -> tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)


@dataclass(frozen=True, slots=True)
class DungeonFloor:
    number: int
    seed: int
    width: int
    height: int
    tiles: tuple[str, ...]
    rooms: tuple[DungeonRoom, ...]
    start_room_id: str
    exit_room_id: str

    def room(self, room_id: str) -> DungeonRoom | None:
        return next((room for room in self.rooms if room.id == room_id), None)

    def tile_at(self, x: int, y: int) -> str:
        if x < 0 or y < 0 or x >= self.width or y >= self.height:
            raise IndexError("coordenada fora do andar")
        return self.tiles[y][x]


@dataclass(frozen=True, slots=True)
class DungeonRun:
    """Metadados da expedição; o estado autoritativo do personagem fica separado."""

    id: str
    player_character_id: str
    seed: int
    current_floor: int = 1
    current_room_id: str | None = None
    status: RunStatus = RunStatus.ACTIVE

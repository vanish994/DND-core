"""Geração procedural reproduzível de andares em grade top-down.

Este módulo gera geometria e tipos de sala, não encontros nem regras de D&D.
Combate, monstros e recompensas serão conectados aos catálogos e resolvedores
existentes numa camada de aplicação posterior.
"""

from __future__ import annotations

import random

from .models import DungeonFloor, DungeonRoom, RoomKind


class DungeonGenerator:
    """Gera um mapa com salas conectadas, a partir de uma seed explícita."""

    WALL = "#"
    FLOOR = "."

    def __init__(self, width: int = 52, height: int = 32, min_rooms: int = 6, max_rooms: int = 10) -> None:
        if width < 32 or height < 22:
            raise ValueError("o mapa precisa ter pelo menos 32x22 tiles")
        if min_rooms < 4 or max_rooms < min_rooms:
            raise ValueError("min_rooms deve ser >= 4 e max_rooms >= min_rooms")
        if max_rooms > 12:
            raise ValueError("max_rooms não pode exceder os 12 espaços do gerador")
        self.width = width
        self.height = height
        self.min_rooms = min_rooms
        self.max_rooms = max_rooms

    def generate(self, floor_number: int, seed: int) -> DungeonFloor:
        if floor_number < 1:
            raise ValueError("floor_number deve ser >= 1")

        rng = random.Random(seed)
        grid = [[self.WALL for _ in range(self.width)] for _ in range(self.height)]
        slots = self._slots()
        rng.shuffle(slots)
        count = rng.randint(self.min_rooms, self.max_rooms)
        raw_rooms: list[DungeonRoom] = []

        for index, (slot_x, slot_y, slot_w, slot_h) in enumerate(slots[:count]):
            room_w = rng.randint(5, min(9, slot_w - 2))
            room_h = rng.randint(4, min(7, slot_h - 2))
            x = slot_x + rng.randint(1, slot_w - room_w - 1)
            y = slot_y + rng.randint(1, slot_h - room_h - 1)
            raw_rooms.append(
                DungeonRoom(
                    id=f"f{floor_number}-r{index + 1}",
                    kind=RoomKind.EVENT,
                    x=x,
                    y=y,
                    width=room_w,
                    height=room_h,
                )
            )

        # Ordem estável por índice: conecta todas as salas e permite caminhos extras.
        rooms = self._assign_kinds(raw_rooms, floor_number)
        adjacency: dict[str, list[str]] = {room.id: [] for room in rooms}
        for left, right in zip(rooms, rooms[1:]):
            adjacency[left.id].append(right.id)
            adjacency[right.id].append(left.id)
            self._carve_corridor(grid, left.center, right.center, rng)

        # Uma ligação extra cria rotas alternativas sem comprometer conectividade.
        if len(rooms) >= 5:
            left_index = rng.randrange(0, len(rooms) - 2)
            right_index = rng.randrange(left_index + 2, len(rooms))
            left, right = rooms[left_index], rooms[right_index]
            if right.id not in adjacency[left.id]:
                adjacency[left.id].append(right.id)
                adjacency[right.id].append(left.id)
                self._carve_corridor(grid, left.center, right.center, rng)

        rooms = tuple(
            DungeonRoom(
                id=room.id,
                kind=room.kind,
                x=room.x,
                y=room.y,
                width=room.width,
                height=room.height,
                connections=tuple(adjacency[room.id]),
            )
            for room in rooms
        )
        for room in rooms:
            self._carve_room(grid, room)

        return DungeonFloor(
            number=floor_number,
            seed=seed,
            width=self.width,
            height=self.height,
            tiles=tuple("".join(row) for row in grid),
            rooms=rooms,
            start_room_id=rooms[0].id,
            exit_room_id=rooms[-1].id,
        )

    def _slots(self) -> list[tuple[int, int, int, int]]:
        usable_width = self.width - 2
        usable_height = self.height - 2
        cols, rows = 4, 3
        cell_w = usable_width // cols
        cell_h = usable_height // rows
        return [
            (1 + col * cell_w, 1 + row * cell_h, cell_w, cell_h)
            for row in range(rows)
            for col in range(cols)
        ]

    @staticmethod
    def _assign_kinds(rooms: list[DungeonRoom], floor_number: int) -> tuple[DungeonRoom, ...]:
        assigned: list[DungeonRoom] = []
        last = len(rooms) - 1
        for index, room in enumerate(rooms):
            if index == 0:
                kind = RoomKind.START
            elif index == last:
                kind = RoomKind.STAIRS
            elif floor_number % 5 == 0 and index == last - 1:
                kind = RoomKind.BOSS
            else:
                kind = (RoomKind.COMBAT, RoomKind.TREASURE, RoomKind.EVENT)[(index - 1) % 3]
            assigned.append(
                DungeonRoom(
                    id=room.id,
                    kind=kind,
                    x=room.x,
                    y=room.y,
                    width=room.width,
                    height=room.height,
                )
            )
        return tuple(assigned)

    def _carve_room(self, grid: list[list[str]], room: DungeonRoom) -> None:
        for y in range(room.y, room.y + room.height):
            for x in range(room.x, room.x + room.width):
                grid[y][x] = self.FLOOR

    def _carve_corridor(
        self,
        grid: list[list[str]],
        start: tuple[int, int],
        end: tuple[int, int],
        rng: random.Random,
    ) -> None:
        x, y = start
        end_x, end_y = end
        if rng.choice((True, False)):
            horizontal_first = True
        else:
            horizontal_first = False
        if horizontal_first:
            while x != end_x:
                grid[y][x] = self.FLOOR
                x += 1 if end_x > x else -1
            while y != end_y:
                grid[y][x] = self.FLOOR
                y += 1 if end_y > y else -1
        else:
            while y != end_y:
                grid[y][x] = self.FLOOR
                y += 1 if end_y > y else -1
            while x != end_x:
                grid[y][x] = self.FLOOR
                x += 1 if end_x > x else -1
        grid[end_y][end_x] = self.FLOOR

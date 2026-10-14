"""Tabuleiro tático puro: geometria de mapa, sem importar regras de D&D.

A convenção de distância é injetada pela camada de integração. Isso permite
testar o tabuleiro isoladamente e mantém o Rule Engine fora deste módulo.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Iterable


DistanceInSquares = Callable[[int, int], int]


@dataclass(frozen=True, slots=True, order=True)
class BoardPosition:
    x: int
    y: int


@dataclass(frozen=True, slots=True)
class CombatBoard:
    width: int
    height: int
    blocked: frozenset[BoardPosition] = frozenset()
    tile_feet: int = 5
    distance_in_squares: DistanceInSquares | None = field(default=None, compare=False, repr=False)
    vision_blocked: frozenset[BoardPosition] = frozenset()

    def __post_init__(self) -> None:
        if self.width < 1 or self.height < 1:
            raise ValueError("O tabuleiro precisa ter dimensões positivas")
        if self.tile_feet < 1:
            raise ValueError("tile_feet precisa ser positivo")
        if any(not self.in_bounds(pos) for pos in self.blocked):
            raise ValueError("Há obstáculos fora do tabuleiro")
        if any(not self.in_bounds(pos) for pos in self.vision_blocked):
            raise ValueError("Há obstáculos de visão fora do tabuleiro")

    def in_bounds(self, pos: BoardPosition) -> bool:
        return 0 <= pos.x < self.width and 0 <= pos.y < self.height

    def is_walkable(self, pos: BoardPosition) -> bool:
        return self.in_bounds(pos) and pos not in self.blocked

    def line_positions(self, origin: BoardPosition, target: BoardPosition) -> tuple[BoardPosition, ...]:
        """Casas atravessadas pelo segmento entre origem e destino (inclusive)."""
        if not self.in_bounds(origin) or not self.in_bounds(target):
            raise ValueError("Posição fora do tabuleiro")
        x0, y0 = origin.x, origin.y
        x1, y1 = target.x, target.y
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x1 > x0 else -1 if x1 < x0 else 0
        sy = 1 if y1 > y0 else -1 if y1 < y0 else 0
        x, y = x0, y0
        positions = [BoardPosition(x, y)]
        ix, iy = 0, 0
        while ix < dx or iy < dy:
            decision = (1 + 2 * ix) * dy - (1 + 2 * iy) * dx
            if decision == 0:
                x += sx
                y += sy
                ix += 1
                iy += 1
            elif decision < 0:
                x += sx
                ix += 1
            else:
                y += sy
                iy += 1
            positions.append(BoardPosition(x, y))
        return tuple(positions)

    def has_line_of_sight(self, origin: BoardPosition, target: BoardPosition) -> bool:
        """Verifica se nenhuma casa intermediária bloqueia a visão."""
        caminho = self.line_positions(origin, target)
        return all(pos not in self.vision_blocked for pos in caminho[1:-1])

    def has_cover_obstacle(
        self,
        origin: BoardPosition,
        target: BoardPosition,
        *,
        occupied: Iterable[BoardPosition] = (),
    ) -> bool:
        """Indica se há obstáculo parcial (pilar, tocha ou criatura) entre origem e destino."""
        intermediarias = self.line_positions(origin, target)[1:-1]
        if not intermediarias:
            return False
        obstaculos_parciais = (self.blocked - self.vision_blocked) | (set(occupied) - {origin, target})
        return any(pos in obstaculos_parciais for pos in intermediarias)

    def distance_feet(self, origin: BoardPosition, target: BoardPosition) -> int:
        """Delega a convenção mecânica de distância à integração configurada."""
        if not self.in_bounds(origin) or not self.in_bounds(target):
            raise ValueError("Posição fora do tabuleiro")
        if self.distance_in_squares is None:
            raise RuntimeError("Configure a distância através da camada de integração")
        return self.distance_in_squares(target.x - origin.x, target.y - origin.y) * self.tile_feet

    def reachable_positions(
        self,
        origin: BoardPosition,
        movement_feet: int,
        *,
        occupied: Iterable[BoardPosition] = (),
    ) -> dict[BoardPosition, int]:
        """Retorna posições alcançáveis e custo em pés, contornando paredes/unidades."""
        if not self.is_walkable(origin):
            raise ValueError("A posição inicial não é caminhável")
        if movement_feet < 0:
            raise ValueError("O deslocamento não pode ser negativo")

        occupied_set = set(occupied) - {origin}
        max_steps = movement_feet // self.tile_feet
        distances: dict[BoardPosition, int] = {origin: 0}
        queue = deque([origin])
        directions = ((1, 0), (-1, 0), (0, 1), (0, -1),
                      (1, 1), (1, -1), (-1, 1), (-1, -1))

        while queue:
            current = queue.popleft()
            steps = distances[current] // self.tile_feet
            if steps >= max_steps:
                continue
            for dx, dy in directions:
                next_pos = BoardPosition(current.x + dx, current.y + dy)
                if next_pos in distances or next_pos in occupied_set:
                    continue
                if not self.is_walkable(next_pos):
                    continue
                if dx and dy:
                    side_a = BoardPosition(current.x + dx, current.y)
                    side_b = BoardPosition(current.x, current.y + dy)
                    if not self.is_walkable(side_a) or not self.is_walkable(side_b):
                        continue
                distances[next_pos] = (steps + 1) * self.tile_feet
                queue.append(next_pos)

        return distances

    def shortest_path(
        self,
        origin: BoardPosition,
        target: BoardPosition,
        *,
        occupied: Iterable[BoardPosition] = (),
    ) -> tuple[BoardPosition, ...] | None:
        """Retorna caminho incluindo origem e destino, ou None se bloqueado."""
        if not self.is_walkable(origin) or not self.is_walkable(target):
            return None
        occupied_set = set(occupied) - {origin}
        if target in occupied_set:
            return None
        parents: dict[BoardPosition, BoardPosition | None] = {origin: None}
        queue = deque([origin])
        directions = ((1, 0), (-1, 0), (0, 1), (0, -1),
                      (1, 1), (1, -1), (-1, 1), (-1, -1))

        while queue:
            current = queue.popleft()
            if current == target:
                path: list[BoardPosition] = []
                cursor: BoardPosition | None = target
                while cursor is not None:
                    path.append(cursor)
                    cursor = parents[cursor]
                return tuple(reversed(path))
            for dx, dy in directions:
                next_pos = BoardPosition(current.x + dx, current.y + dy)
                if next_pos in parents or next_pos in occupied_set or not self.is_walkable(next_pos):
                    continue
                if dx and dy:
                    if not self.is_walkable(BoardPosition(current.x + dx, current.y)):
                        continue
                    if not self.is_walkable(BoardPosition(current.x, current.y + dy)):
                        continue
                parents[next_pos] = current
                queue.append(next_pos)
        return None

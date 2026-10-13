"""Tabuleiro tático discreto para encontros; não resolve regras de combate.

A geometria usa casas de 5 pés e delega o cálculo de distância ao helper
existente do Rule Engine. A UI pode ocultar a grade até selecionar movimento
ou uma magia. Este módulo só valida posições e caminhos no tabuleiro.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Iterable

from rule_engine.combat_geometry import distancia_grade


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

    def __post_init__(self) -> None:
        if self.width < 1 or self.height < 1:
            raise ValueError("O tabuleiro precisa ter dimensões positivas")
        if self.tile_feet < 1:
            raise ValueError("tile_feet precisa ser positivo")
        if any(not self.in_bounds(pos) for pos in self.blocked):
            raise ValueError("Há obstáculos fora do tabuleiro")

    def in_bounds(self, pos: BoardPosition) -> bool:
        return 0 <= pos.x < self.width and 0 <= pos.y < self.height

    def is_walkable(self, pos: BoardPosition) -> bool:
        return self.in_bounds(pos) and pos not in self.blocked

    def distance_feet(self, origin: BoardPosition, target: BoardPosition) -> int:
        """Distância de combate em pés, conforme a convenção de grade do motor."""
        if not self.in_bounds(origin) or not self.in_bounds(target):
            raise ValueError("Posição fora do tabuleiro")
        return distancia_grade(target.x - origin.x, target.y - origin.y) * self.tile_feet

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
                # A convenção atual do motor trata cada diagonal como uma casa.
                # Restrições de passagem diagonal entre dois obstáculos são
                # aplicadas para evitar atravessar cantos fechados.
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
        occupied_set = set(occupied) - {origin, target}
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

"""Ciclo de turnos do encontro; nenhuma regra de ataque/dano é resolvida aqui."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Callable, Mapping

from .combat_board import BoardPosition, CombatBoard
from .rule_adapter import DungeonRuleAdapter


class EncounterStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    DEFEATED = "defeated"


@dataclass(frozen=True, slots=True)
class Combatant:
    id: str
    position: BoardPosition
    initiative: int
    is_player: bool = False


class CombatSession:
    """Controla ordem, posição e encaminhamento de ações para o adaptador."""

    def __init__(self, board: CombatBoard, combatants: list[Combatant]) -> None:
        if len(combatants) < 2:
            raise ValueError("Um encontro precisa de pelo menos dois combatentes")
        ids = [combatant.id for combatant in combatants]
        if any(not combatant_id for combatant_id in ids) or len(ids) != len(set(ids)):
            raise ValueError("IDs de combatentes devem ser únicos e não vazios")
        positions = [combatant.position for combatant in combatants]
        if len(positions) != len(set(positions)):
            raise ValueError("Dois combatentes não podem ocupar a mesma casa")
        if any(not board.is_walkable(position) for position in positions):
            raise ValueError("Combatente fora do tabuleiro ou em casa bloqueada")
        if sum(combatant.is_player for combatant in combatants) != 1:
            raise ValueError("O encontro solo exige exatamente um personagem do jogador")

        # Desempates preservam a ordem recebida; a iniciativa é calculada fora
        # deste módulo, através dos resolvedores canônicos.
        self.board = board
        self.combatants = sorted(combatants, key=lambda item: item.initiative, reverse=True)
        self._defeated: set[str] = set()
        self.round_number = 1
        self._turn_index = 0
        self.status = EncounterStatus.ACTIVE

    @property
    def current_combatant(self) -> Combatant | None:
        if self.status is not EncounterStatus.ACTIVE:
            return None
        return self.combatants[self._turn_index]

    def occupied_positions(self, *, excluding: str | None = None) -> frozenset[BoardPosition]:
        return frozenset(
            combatant.position
            for combatant in self.combatants
            if combatant.id != excluding and combatant.id not in self._defeated
        )

    def resolve_action(
        self,
        adapter: DungeonRuleAdapter,
        actor_id: str,
        facts: Mapping[str, Any],
        *,
        characters: list[dict[str, Any]] | None = None,
        on_change: Callable[[dict[str, Any], dict[str, Any]], None] | None = None,
    ):
        """Encaminha a ação atual; não consome turno nem interpreta regras localmente."""
        current = self.current_combatant
        if current is None:
            raise RuntimeError("O encontro não está ativo")
        if actor_id != current.id:
            raise ValueError("Não é o turno desse combatente")
        action_facts = dict(facts)
        action_facts.setdefault("character_id", actor_id)
        return adapter.execute_rule(action_facts, characters=characters, on_change=on_change)

    def end_turn(self, actor_id: str) -> None:
        current = self.current_combatant
        if current is None:
            raise RuntimeError("O encontro não está ativo")
        if actor_id != current.id:
            raise ValueError("Só o combatente atual pode encerrar o turno")
        self._advance_to_next_active()

    def mark_defeated(self, combatant_id: str) -> None:
        """Registra um estado de derrota já confirmado pela fonte autoritativa."""
        if combatant_id not in {combatant.id for combatant in self.combatants}:
            raise KeyError(f"Combatente desconhecido: {combatant_id}")
        self._defeated.add(combatant_id)
        players = {combatant.id for combatant in self.combatants if combatant.is_player}
        enemies_alive = {combatant.id for combatant in self.combatants if not combatant.is_player} - self._defeated
        if players <= self._defeated:
            self.status = EncounterStatus.DEFEATED
        elif not enemies_alive:
            self.status = EncounterStatus.COMPLETED
        elif self.current_combatant and self.current_combatant.id in self._defeated:
            self._advance_to_next_active()

    def _advance_to_next_active(self) -> None:
        if self.status is not EncounterStatus.ACTIVE:
            return
        for _ in range(len(self.combatants)):
            self._turn_index += 1
            if self._turn_index >= len(self.combatants):
                self._turn_index = 0
                self.round_number += 1
            candidate = self.combatants[self._turn_index]
            if candidate.id not in self._defeated:
                return
        self.status = EncounterStatus.COMPLETED

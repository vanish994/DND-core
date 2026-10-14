"""Fronteira explícita entre o jogo de dungeon e os sistemas canônicos de D&D.

O jogo depende deste adaptador, nunca do Rule Engine diretamente. Este módulo
não implementa mecânicas: traduz chamadas para os contratos do Orquestrador.
"""
from __future__ import annotations

from typing import Any, Callable, Mapping

from orchestrator import Acao, OrquestradorAcoes, ResultadoAcao
from rule_engine.combat_geometry import distancia_grade

from .combat_board import BoardPosition, CombatBoard


class DungeonRuleAdapter:
    """Adapta a geometria e as ações do jogo às APIs canônicas existentes."""

    def __init__(self, orchestrator: OrquestradorAcoes | None = None) -> None:
        self.orchestrator = orchestrator or OrquestradorAcoes()

    @staticmethod
    def create_combat_board(
        width: int,
        height: int,
        *,
        blocked: frozenset[BoardPosition] = frozenset(),
        vision_blocked: frozenset[BoardPosition] = frozenset(),
        tile_feet: int = 5,
    ) -> CombatBoard:
        """Injeta no tabuleiro a convenção de distância do Rule Engine."""
        return CombatBoard(
            width=width,
            height=height,
            blocked=blocked,
            vision_blocked=vision_blocked,
            tile_feet=tile_feet,
            distance_in_squares=distancia_grade,
        )

    def execute_rule(
        self,
        facts: Mapping[str, Any],
        *,
        characters: list[dict[str, Any]] | None = None,
        on_change: Callable[[dict[str, Any], dict[str, Any]], None] | None = None,
    ) -> ResultadoAcao:
        """Encaminha fatos de uma ação ao Orquestrador sem resolver regras localmente."""
        action = Acao.de_ferramenta("resolver_regra", {"fatos": dict(facts)})
        return self.orchestrator.executar(
            action,
            personagens=characters,
            on_alteracao=on_change,
        )

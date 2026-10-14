"""Regressions for the standardized tactical combat maps."""

from dungeon_game.encontro import (
    SALAS_PADRAO,
    carregar_mapa,
    inimigos_padrao_do_mapa,
    listar_mapas,
)


LARGURA_PADRAO = 48
ALTURA_PADRAO = 28


def test_catalog_maps_share_standard_dimensions():
    mapas = listar_mapas()
    assert mapas
    assert all(mapa["largura"] == LARGURA_PADRAO for mapa in mapas)
    assert all(mapa["altura"] == ALTURA_PADRAO for mapa in mapas)


def test_player_and_enemy_spawns_are_inside_walkable_cells():
    for mapa_id in SALAS_PADRAO:
        mapa = carregar_mapa(mapa_id)
        grade = mapa["grade"]
        legenda = mapa["legenda"]
        posicoes = list(mapa.get("entradas", {}).get("jogador", []))
        posicoes += [
            {"x": x, "y": y}
            for _, _, (x, y) in inimigos_padrao_do_mapa(mapa_id)
        ]
        for posicao in posicoes:
            x, y = posicao["x"], posicao["y"]
            assert 0 <= x < LARGURA_PADRAO
            assert 0 <= y < ALTURA_PADRAO
            simbolo = grade[y][x]
            assert not legenda.get(simbolo, {}).get("bloqueia_movimento", False), (
                f"{mapa_id}: spawn bloqueado em ({x}, {y})"
            )

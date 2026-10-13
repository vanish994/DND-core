# Tabuleiro de combate — primeiro incremento

O jogo usa uma tela de combate separada da progressão por andares. O tabuleiro é uma grade tática discreta em pixel art; a interface pode deixar as linhas quase invisíveis e destacá-las apenas ao selecionar movimento ou uma magia.

## Limites de responsabilidade

- `dungeon_game/combat_board.py`: dimensões, casas bloqueadas, posições, distância em casas de 5 pés e caminhos alcançáveis.
- `rule_engine/combat_geometry.py`: continua sendo a fonte do cálculo de distância em grade.
- `orchestrator/`: permanece responsável por executar ações estruturadas e aplicar resultados mecânicos.
- A camada visual não calcula ataque, dano, CA, CD, custo de magia nem condições.

Este incremento não implementa ainda a resolução de turnos ou ataques. Ele estabelece a geometria usada para selecionar movimento e alvos; a próxima etapa deve conectar comandos de combate ao Orquestrador e testar o fluxo completo.

## Convenções atuais

- Cada casa representa 5 pés.
- Movimento usa caminho em oito direções, impedindo cortar diagonalmente entre obstáculos.
- Casas bloqueadas e ocupadas não são destinos válidos.
- O custo de movimento respeita o orçamento de deslocamento em pés.
- O cálculo de distância delega a `distancia_grade` existente, evitando duplicar essa regra.

Antes de lançar, validar a convenção de diagonais e linha de efeito contra a edição de D&D configurada, e adicionar testes de cobertura e alcance de magias usando os resolvedores existentes.

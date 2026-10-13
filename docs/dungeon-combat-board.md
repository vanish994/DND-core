# Tabuleiro de combate — primeiro incremento

O jogo usa uma tela de combate separada da progressão por andares. O tabuleiro é uma grade tática discreta em pixel art; a interface pode deixar as linhas quase invisíveis e destacá-las apenas ao selecionar movimento ou uma magia.

## Limites de responsabilidade

- `dungeon_game/combat_board.py`: dimensões, casas bloqueadas, posições e caminhos. Não importa módulos do Rule Engine nem decide a convenção mecânica de distância.
- `dungeon_game/rule_adapter.py`: fronteira explícita para o Rule Engine e o Orquestrador. Injeta a função canônica de distância e traduz fatos para o contrato `Acao`.
- `rule_engine/combat_geometry.py`: continua sendo a fonte do cálculo de distância em grade.
- `orchestrator/`: executa ações estruturadas e aplica resultados mecânicos.
- A camada visual não calcula ataque, dano, CA, CD, custo de magia nem condições.

## Convenções atuais

- Cada casa representa 5 pés por padrão.
- Movimento usa caminho em oito direções, impedindo cortar diagonalmente entre obstáculos.
- Casas bloqueadas e ocupadas não são destinos válidos.
- O custo de movimento respeita o orçamento de deslocamento em pés.
- A convenção de distância é injetada pelo adaptador; o tabuleiro não importa o Rule Engine diretamente.

## Estado deste incremento

O adaptador agora encaminha ações estruturadas ao Orquestrador, mas isso ainda não constitui um combate jogável. Permanecem pendentes o serviço de expedição, estado de turnos, seleção de ações, IA convencional dos inimigos, interface pixel art, persistência e testes ponta a ponta. Não adicionar resoluções locais de ataque ou dano para preencher essas lacunas.

Antes de lançar, validar a convenção de diagonais e linha de efeito contra a edição de D&D configurada, e adicionar testes de cobertura e alcance de magias usando os resolvedores existentes.

# Arquitetura inicial — RPG de Dungeon

## Objetivo do primeiro incremento

Construir um RPG solo, de visão superior (top-down), com andares procedurais. O jogador controla um único personagem; o sistema administra mapa, salas, encontros, recompensas e progressão. O Rule Engine existente continua sendo a autoridade mecânica de D&D.

Este incremento cria somente o núcleo de domínio e a geração geométrica de andares. Não declara o jogo jogável ainda: renderização, movimentação do jogador, encontros reais, persistência da expedição e integração ponta a ponta ainda são etapas futuras.

## Limites entre camadas

```text
Interface top-down (futura)
    | comandos de jogador
    v
Aplicação do jogo / GameService (futura)
    | coordena fluxo, valida estado de jogo, salva expedição
    +------> DungeonGenerator / modelos de dungeon
    |
    +------> OrquestradorAcoes
                 |
                 v
             Rule Engine
                 |
                 v
        resultado mecânico determinístico
```

### Responsabilidades

- **`dungeon_game/`**: geometria e domínio da expedição. Gera salas, corredores, tipos de sala e metadados. Não contém regras de D&D, dano, CA, XP ou decisões de combate.
- **`rule_engine/`**: calcula e valida regras mecânicas, através da API existente.
- **`orchestrator/`**: recebe ações estruturadas, prepara fatos, chama o motor e aplica alterações mecânicas ao estado canônico. Não deve ser duplicado nem contornado.
- **`character_creator/`**: continua sendo o fluxo existente de criação de fichas. O jogo deve referenciar a ficha por ID, sem criar um segundo criador.
- **Persistência da expedição (futura)**: guarda seed, andar atual, sala, posição, progresso das salas, inimigos, loot e status da run. A ficha e os recursos mecânicos devem continuar coerentes com a fonte autoritativa usada pelo projeto.
- **Interface (futura)**: apenas apresenta mapa/estado e envia comandos; não calcula ataques, dano, espaços ou pré-requisitos.

## Geração procedural atual

`DungeonGenerator.generate(floor_number, seed)` produz um `DungeonFloor` imutável:

- grade de tiles: `#` é parede e `.` é chão caminhável;
- salas com IDs estáveis para a combinação andar/índice;
- corredores conectando todas as salas;
- tipos de sala: início, combate, tesouro, evento, chefe e escada;
- sala de chefe em cada quinto andar;
- mesma seed + mesmo número de andar + mesma configuração = mesmo resultado.

A geometria é independente da resolução mecânica. Uma sala do tipo combate ainda não cria monstros automaticamente; o futuro serviço de encontros consultará o bestiário e usará os sistemas de encontro já presentes no Rule Engine, evitando inventar estatísticas.

## Fluxo futuro de jogo

1. Jogador seleciona uma ficha existente e inicia uma expedição com seed.
2. O jogo gera o andar e coloca o personagem na sala inicial.
3. Comandos de exploração atualizam posição e sala, sem resolver regras de D&D desnecessárias.
4. Ao entrar numa sala de combate, o serviço monta o encontro a partir do bestiário/catálogos existentes.
5. Cada ação de combate vira uma ação estruturada processada pelo `OrquestradorAcoes`; o resultado validado atualiza o estado e é persistido.
6. Ao limpar uma sala, o serviço marca a sala concluída e disponibiliza eventos/recompensas apropriados.
7. A escada leva ao próximo andar, mantendo a mesma expedição e ficha.
8. Derrota, conclusão ou retorno seguro encerram/pausam a expedição segundo regras de produto explícitas.

## Contrato de dados

- `DungeonRun`: ID da expedição, ID da ficha controlada, seed, andar atual, sala atual e status.
- `DungeonFloor`: dimensões, grade, salas, início e saída.
- `DungeonRoom`: ID, tipo, retângulo e conexões.
- O estado de personagem não é copiado para o mapa como uma segunda ficha autoritativa. A camada de aplicação coordena o estado do jogo e usa a integração já existente do Orquestrador para alterações mecânicas.

## Próximos incrementos recomendados

1. **Serviço de expedição**: criar/retomar run, carregar o andar a partir da seed, rastrear posição top-down e validar movimento entre tiles caminháveis.
2. **Persistência SQLite de dungeon**: tabelas isoladas para runs, salas descobertas, posição e estado de encontros; referenciar a ficha existente por ID. Transações e retomada após reinício.
3. **Adaptador de combate**: converter comandos do jogador em `Acao` e chamar `OrquestradorAcoes`; nunca calcular ataques/dano diretamente na UI ou no gerador.
4. **Inimigos determinísticos**: estratégia simples por estado/heurísticas para decidir ações inimigas; toda resolução mecânica continua no motor.
5. **Renderização top-down**: desenhar a grade, personagem, portas, inimigos, tesouros, interface de turno e feedback do motor.
6. **Loop ponta a ponta**: entrar no andar, mover, encontrar inimigo, lutar, ganhar recompensa, descer, salvar e retomar.

## Critérios de aceitação deste incremento

- geração determinística com seed;
- início e escada sempre presentes;
- todas as salas alcançáveis por tiles caminháveis;
- sala de chefe a cada cinco andares;
- entradas inválidas rejeitadas;
- testes focados na geração, sem depender de IA generativa nem modificar o Rule Engine.

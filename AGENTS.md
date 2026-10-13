# Guia de desenvolvimento para agentes — DND Core

Este arquivo orienta agentes que investigam, implementam ou revisam mudanças neste repositório. Leia também o `README.md` e os documentos de domínio relevantes antes de alterar código.

## Objetivo do produto

Construir um RPG de turnos estilo *idle dungeon crawler* baseado em D&D 2024 (5.5e): o jogador decide as ações do Bardo; encontros usam mapas fixos em grade e inimigos executam turnos autônomos determinísticos. A progressão desejada é por salas/andares. **Não** adicionar exploração livre nem movimento manual fora do combate.

## Invariantes de arquitetura e regras

- `rule_engine/` é a autoridade para validar regras, opções e resultados mecânicos. Reutilize-o; não replique regras de D&D em JavaScript, rotas HTTP ou IA de monstros.
- `orchestrator/` coordena ações e aplica mutações de ficha/recursos. Não contorne o Orquestrador para alterar PV, slots ou outros recursos.
- `dungeon_game/encontro.py` é a camada de domínio do encontro: estado de combate, turno, movimento e ações. `dungeon_game/servidor.py` deve traduzir HTTP para chamadas de domínio, não tomar decisões táticas.
- `dungeon_game/combat_session.py` e o adaptador de tabuleiro mantêm a iniciativa e a geometria tática. Uma casa representa **5 pés**; use o tabuleiro para medir movimento, alcance e ocupação.
- `dungeon_game/combate_inimigo.py` contém comportamento convencional/determinístico. Não introduza LLMs ou aleatoriedade não reprodutível no turno dos monstros.
- `dungeon_game/web/` apresenta o snapshot do servidor e envia ações. O cliente não é fonte de verdade; sempre mostre o estado devolvido pela API.
- Bardo é a classe inicial obrigatória do protótipo. Não adicionar seleção de classe sem uma mudança de produto explicitamente aprovada.
- Mapas vêm do catálogo fixo em `dungeon_game/mapas/`; não reintroduza geração procedural como substituta do catálogo.

## Onde procurar

- `README.md`: instalação, comandos e visão geral.
- `RULE_ENGINE.md`: contratos e fatos aceitos pelo motor.
- `docs/DUNGEON_GAME_ARCHITECTURE.md`: limites e arquitetura do jogo.
- `docs/dungeon-combat-board.md`: convenções do tabuleiro tático.
- `docs/RENDER_DEPLOYMENT.md`: Blueprint e configuração do host persistente.
- `rule_engine/`, `orchestrator/`, `dungeon_game/`: implementação; `tests/`: contratos e regressões.

Antes de mudar uma mecânica, procure primeiro por implementação e testes existentes com `rg`. Estenda o contrato canônico mais próximo e escreva regressões para a regra e para o fluxo HTTP/UI afetado. Preserve as limitações que o sistema realmente implementa; não apresente efeitos parciais como regras completas.

## Desenvolvimento e verificação

Requer Python 3.11 ou superior. A aplicação de combate local pode ser iniciada com:

```bash
PORT=8100 python -m dungeon_game.servidor
```

Abra `http://localhost:8100/encontro`. O criador de personagens separado usa `python -m character_creator`.

Antes de concluir uma alteração, rode os checks aplicáveis:

```bash
python -m compileall -q dungeon_game rule_engine orchestrator character_creator tests
python -m unittest discover -s tests -v
node --check dungeon_game/web/app.js
ruff check <arquivos-alterados>
git diff --check
```

Ruff e ferramentas relacionadas estão em `requirements-dev.txt`. Para testes de persistência, use SQLite dentro de `tempfile.TemporaryDirectory`; nunca a base real ou uma URL de produção.

## Persistência e hospedagem

- Sem configuração, sessões usam memória, o que é adequado apenas para desenvolvimento/testes e perde estado ao reiniciar.
- `DND_CORE_DATABASE=/caminho/absoluto/sessoes.sqlite3` seleciona SQLite local; `DATABASE_URL` seleciona PostgreSQL. O servidor persiste snapshots e os reconstitui a cada requisição.
- No Render, `render.yaml` exige `DND_REQUIRE_PERSISTENCE=true` e um `DATABASE_URL` secreto. Não dependa do filesystem efêmero do serviço para dados de jogo.
- Nunca inclua `.env`, URLs de banco, tokens ou credenciais em commits, logs, fixtures, PRs ou respostas. Use os campos de segredo do host.
- A demo ainda não tem autenticação de contas; o ID aleatório da sessão é a credencial de acesso ao encontro. Não anuncie um link de partida como privado se ele foi publicado publicamente.
- Não crie contas, bancos, serviços pagos, não altere planos e não publique uma URL pública sem autorização explícita do usuário. A PR/Blueprint não substitui essa autorização.

## Workflow Git

- Confira `git status`, branch e `git log` antes de editar; não descarte mudanças preexistentes.
- Trabalhe em branch curta baseada no `origin/main` atualizado. Use commits pequenos, focados e com mensagens convencionais (`feat:`, `fix:`, `test:`, `docs:`, `chore:`).
- Rode testes antes do commit; revise `git diff` e procure segredos no staged diff.
- Abra PRs revisáveis quando apropriado. **Não faça merge de `main` nem deploy automático**, a menos que o usuário peça ou autorize claramente.
- Ao relatar o trabalho, liste mudanças, validações, pendências e itens intencionalmente não alterados.

## Próximos incrementos conhecidos

Considere estas tarefas como opções, não como autorização para ampliar escopo automaticamente:

1. Implementar táticas de ataque à distância do Esqueleto sob as mesmas validações geométricas do motor.
2. Consolidar XP/ouro e transição entre salas/andares.
3. Revisar carregamento e seleção de mapas do catálogo.
4. Integrar o deploy Render/PostgreSQL após a revisão/merge da mudança de persistência e autorização explícita para criar/configurar os recursos externos.

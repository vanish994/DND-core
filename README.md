# DND Core

Núcleo mecânico determinístico para D&D, com uma experiência web responsiva de criação de personagens que consome os catálogos e validadores reais do projeto.

## Componentes

- `rule_engine/`: regras, catálogos e resolução mecânica; autoridade sobre opções e resultados.
- `orchestrator/`: coordena ações, pré-condições, aplicação de estado e resultados estruturados.
- `character_creator/`: serviço de criação, API JSON, persistência SQLite e interface em português.
- `tests/`: testes do Rule Engine, do Orquestrador e do fluxo de criação.

A implementação do Mestre de Jogo (MJ), prompts, clientes de LLM e campanhas não fazem parte deste repositório.

## Arquitetura

```text
Interface web responsiva
          |
          v
API WSGI / CharacterCreatorService
          |                         \
          v                          v
Rule Engine --------------------> SQLite
```

O Rule Engine é a autoridade para regras e resultados mecânicos. A interface não duplica custos ou pré-requisitos: consulta os catálogos e envia as escolhas ao serviço, que as revalida antes de criar a ficha. Uma resposta de sucesso de criação só é devolvida depois do `COMMIT` SQLite. O rascunho da interface também é guardado localmente no navegador.

## Criador de personagens

Requer Python 3.11 ou superior. Não depende de framework web externo.

```bash
python -m character_creator
```

Abra `http://localhost:8000`. O servidor escuta em `0.0.0.0`; defina `PORT` (ou `DND_CORE_PORT`) para trocar a porta. O banco padrão fica em `data/characters.sqlite3` — diretório ignorado pelo Git. Para mudar o caminho, use `DND_CORE_DATABASE=/caminho/para/fichas.sqlite3`.

Rotas principais:

- `GET /api/health` e `GET /api/catalog`
- `POST /api/score-preview` e `POST /api/preview`
- `POST /api/characters` (cria apenas após validação do motor e persistência confirmada)
- `GET /api/characters` e `GET /api/characters/<id>`

O fluxo começa no nível 1 para não simular decisões de progressão que a criação atual não valida integralmente. O equipamento inicial por classe também não está catalogado; o serviço valida e registra o pacote A/B do antecedente, sem inventar um kit de classe.

**Artífice:** o criador usa a progressão e os helpers de conjuração existentes, oferece as opções de magia que o motor lista e mostra o mapa de cobertura por nível. A implementação do repositório para Artífice é parcial: infusões, catálogo de itens mágicos e validação da escolha de itens não estão implementados. Subclasses são apresentadas no nível em que ficam disponíveis, sem fingir suporte a detalhes ausentes.

## Uso rápido do motor

```python
from rule_engine import build_default_engine
from orchestrator import Acao, OrquestradorAcoes

engine = build_default_engine()
orquestrador = OrquestradorAcoes(engine)

acao = Acao.de_ferramenta(
    "resolver_regra",
    {"fatos": {"type": "ability_check", "skill": "atletismo", "character_id": "p1"}},
)
resultado = orquestrador.executar(acao, personagens=[])
print(resultado.status, resultado.dados)
```

O formato dos fatos depende da regra chamada; consulte `RULE_ENGINE.md` e os contratos em `orchestrator/contratos.py`.

## Instalação e testes

Para a aplicação e os testes do repositório, basta Python 3.11 ou superior:

```bash
python -m unittest discover -s tests -v
```

As ferramentas opcionais de qualidade estão em `requirements-dev.txt` (Black, isort, Ruff e pytest). A cobertura de regras varia por recurso; o serviço informa limitações no perfil e na ficha em vez de presumir comportamento.

## Origem

Os arquivos de `rule_engine/` e `orchestrator/` foram copiados do repositório [vanish994/DND-projeto-IA](https://github.com/vanish994/DND-projeto-IA), branch `main`, commit `c8bd03bb9df37418af53f2fcb65c787eb002cf51`. Os módulos centrais foram preservados; este repositório não inclui a implementação de MJ.

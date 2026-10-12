# DND Core

Núcleo mecânico independente para um jogo de D&D. Este repositório contém somente:

- `rule_engine/`: regras determinísticas, dados de catálogo e resolução mecânica.
- `orchestrator/`: coordenação de ações, pré-condições, aplicação de estado e resultados estruturados.
- `tests/`: testes selecionados do Rule Engine e do Orquestrador.

A implementação do Mestre de Jogo (MJ), prompts, clientes de LLM, backend conversacional, frontend e dados de campanhas **não fazem parte deste repositório**.

## Arquitetura

```text
Interface / API / testes
          |
          v
    Orquestrador
          |
          v
     Rule Engine
          |
          v
  Resultado estruturado
```

O Rule Engine é a autoridade sobre as regras e resultados mecânicos. O Orquestrador recebe uma ação estruturada (`Acao`), prepara fatos, despacha para o motor e devolve um `ResultadoAcao`. Ele não precisa instanciar nem importar uma implementação de MJ.

## Uso rápido

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

O formato exato dos fatos depende da regra chamada; consulte `RULE_ENGINE.md` e os contratos em `orchestrator/contratos.py`.

## Instalação e testes

Requer Python 3.11 ou superior.

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
```

**Validação inicial:** GitHub Actions executou a suíte deste repositório em Python 3.11: `216 passed, 5 subtests passed`. A suíte contém os testes selecionados do núcleo, não todos os testes do projeto original. A validação cobre importação sem backend/integrações e os testes mecânicos incluídos; novas mudanças devem manter o CI verde.

## Origem

Os arquivos de `rule_engine/` e `orchestrator/` foram copiados do repositório [vanish994/DND-projeto-IA](https://github.com/vanish994/DND-projeto-IA), branch `main`, commit `c8bd03bb9df37418af53f2fcb65c787eb002cf51`. Os módulos centrais foram preservados; este repositório não inclui a implementação de MJ.

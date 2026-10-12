# Rule Engine

Autoridade mecânica determinística do **DND-core**. O motor recebe fatos
estruturados, encontra a regra aplicável de maior prioridade e devolve uma
decisão auditável com trilha de auditoria. As fontes oficiais são o **Livro do
Jogador 2024**, o **Dungeon Master's Guide 2024** e o **SRD 5.2.1** (catálogo
em `biblioteca/README.md`).

## Fluxo

1. A IA transforma a situação narrada em fatos estruturados.
2. O motor avalia as regras, sem inventar uma regra nova durante a resolução.
3. O resultado retorna `status`, `outcome`, regras aplicadas e `trace`.
4. `to_ai_instruction()` produz uma instrução curta para a IA continuar a
   resposta sem contradizer a decisão.

## Exemplo

```python
from rule_engine import build_default_engine

engine = build_default_engine()
result = engine.evaluate({
    "type": "ability_check",
    "roll": 14,
    "modifier": 2,
    "dc": 15,
})

print(result.outcome)
print(result.to_ai_instruction())
```

## Como o motor decide

- As regras são ordenadas por `(-prioridade, rule_id)`; a primeira aplicável
  vence (first-match). O desempate por `rule_id` é estável.
- Exceções em `when` (KeyError/TypeError/ValueError) marcam a regra como
  `ignorada` no `trace` e seguem adiante; exceções em `resolve` propagam para o
  chamador. Fatos sem chave obrigatória devem, portanto, ser validados antes.
- Cada resolução inclui `rule_source` com a fonte da regra.

## Contrato de rolagens

A CD pertence à decisão do MJ; o resultado do d20 pertence ao motor
(`rule_engine/dice.py`). O motor gera o dado com `seed` auditável e
reprodutível; sem CD informada, a resolução volta `result=requires_dc`
(`reason=cd_do_mj_ausente`) e a mesma `seed` reaproveita a rolagem quando o MJ
define a CD. Ataques sem CA do alvo voltam `result=blocked`,
`reason=target_ac_ausente`. Nunca invente `roll` fora do motor.

## Fatos suportados

Famílias registradas em `build_default_engine()` (`rule_engine/rules.py`):

- **Testes de d20** — `ability_check` (roll externo ou `seed` no motor),
  `skill_check`, `passive_check`, `group_check`, `heroic_inspiration`,
  `saving_throw` (roll cru) e `saving_throw_check` (atributo + proficiência),
  `initiative` (roll no motor) e `initiative_check`.
- **Ataque e dano** — `attack` (roll externo ou no motor), `damage` (dados,
  expressão oficial ou crítico), `damage_application` (PV, temporários, morte
  maciça), `damage_defenses` (Imunidade/Resistência/Vulnerabilidade na ordem do
  glossário 2024), `healing`, `death_save`, `stabilize`, `exhaustion`,
  `short_rest`, `long_rest`.
- **Concentração e condições** — `concentration_check`, `condition`
  (aplicar/remover/imunidade), `condition_state` (estado persistente com
  durações e Exaustão), `condition_effect` (efeitos completos sobre ataque,
  movimento, fala e sentidos).
- **Magias** — `spell_cast` (com `magia` resolve componentes, concentração,
  upcasting e espaço; sem `magia`, valida espaço/círculo), `spell_cast_complete`
  (preparação, ritual, componentes), `spell_targets`, `spell_area`,
  `spell_catalog` (list/lookup).
- **Combate** — `opportunity_attack`, `shove`, `grapple`, `grapple_escape`,
  `two_weapon_attack`, `attack_geometry`, `range`, `cover`, `line_of_sight`,
  `fall`, `senses`, `special_movement`, `mounted_combat`, `underwater_attack`,
  `object_damage`, `dodge_action`.
- **Exploração e social** — `hide_action`, `hide_event`, `influence_action`,
  `search_action`, `help_action`, `study_action`.
- **Equipamento e economia** — `armor_class`, `weapon`, `carrying_capacity`,
  `equipment` (lookup/inventory), `economy` (buy/sell), `magic_item`
  (attune/use), `catalog_lookup`, `catalog_list`.
- **Personagem** — `character_creation`, `ability_generation`, `level_up`,
  `multiclass`, `species_traits` (traços completos das 10 espécies do PHB
  2024), `feat` (validate/resolve).
- **Classes** — `class_feature`, `martial_feature` (ataque extra, maestria,
  fúria, fôlego, ataque furtivo, foco, defletir, esquiva, evasão),
  `martial_subclass_feature`, `spellcaster_feature` (progressão, inspiração de
  bardo, canalizar divindade, forma selvagem, livro de magias),
  `advanced_caster_feature` (bruxo, feiticeiro, guardião, paladino),
  `warlock_invocation` (validate/resolve).
- **Bestiário e encontros** — `bestiary` (consulta, blocos do SRD 5.2.1, XP),
  `encounter` (budget/review/attitude/personality/relationships com o
  orçamento de XP do DMG 2024).

## Regras notáveis (2024)

- 20/1 naturais resolvem testes automaticamente; no ataque, 20 é crítico.
- Crítico dobra **todos** os dados de dano e soma modificadores uma única vez.
- Vantagem e desvantagem se cancelam; surpresa impõe desvantagem na iniciativa.
- Resistência e Vulnerabilidade **não se cancelam**: aplica-se primeiro
  ajustes, depois Resistência (metade, para baixo) e por último Vulnerabilidade
  (dobro) — glossário "Resistência e Vulnerabilidade" (PHB 2024). Efeitos do
  mesmo tipo não acumulam; `todos` é curinga nos blocos de defesa.
- Dano Maciço: se o dano reduz a 0 PV e o excedente (após PV Temporários) for
  igual ou superior aos PV máximos, a criatura morre.
- Dano de salvaguarda em área é rolado uma única vez para todos os alvos;
  sucesso costuma reduzir à metade (para baixo).
- Magias sem espaço (`has_slot=False`) ou com círculo acima do espaço disponível
  são bloqueadas, inclusive no caminho com `magia`.
- Exaustão: −2 por nível em d20, −1,5 m por nível de deslocamento, morte no
  nível 6.

## Estado de cobertura

A suíte (`python -m pytest`) valida o núcleo mecânico. Continuam **abertos**
(os efeitos listados devem ser resolvidos caso a caso, com teste por regra):

- efeitos individuais da maioria das 390 magias catalogadas;
- efeitos de talentos ainda sem ramo mecânico próprio (`nao_implementado`);
- características e subclasses além dos lotes já resolvidos em
  `class_features.py`, `martial*.py`, `spellcasters.py`, `advanced_casters.py`;
- listas de magias por classe e equipamento inicial por classe/origem;
- veículos e fabricação detalhada.

A conclusão de uma regra exige: implementação no módulo correto, registro em
`rules.py`, teste determinístico, saída auditável e atualização deste inventário.

## Próximas extensões

- listas de magias por classe e progressões derivadas;
- efeitos mecânicos das magias restantes;
- integração de recursos de classe com descansos (contrato de recursos);
- separação por edição (`2024`) e configuração da mesa;
- carregamento de regras em JSON/YAML com versionamento e fonte.

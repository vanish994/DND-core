# Biblioteca de referência do Rule Engine

Esta pasta reúne o catálogo de fontes para o agente de desenvolvimento consultar ao auditar e melhorar o `rule_engine/`.

## Fontes identificadas no repositório original

Os links abaixo apontam para os arquivos que já existem no repositório de origem. **Os arquivos completos não foram duplicados neste repositório**; antes de copiar livros integrais para este repositório público, confirme que você tem autorização para redistribuí-los.

1. **Livro do Jogador 2024** — [PDF no repositório original](https://github.com/vanish994/DND-projeto-IA/blob/main/dampd-5e---livro-do-jogador-2024.pdf)
2. **Dungeon Master's Guide 2024** — [arquivo de texto no repositório original](https://github.com/vanish994/DND-projeto-IA/blob/main/Dungeon_Masters_Guide_2024.txt)
3. **Eberron: Forge of the Artificer** — [arquivo de texto no repositório original](https://github.com/vanish994/DND-projeto-IA/blob/main/Full%20text%20of%20_Eberron_%20Forge%20of%20the%20Artificer.txt)
4. **Ravenloft** — [arquivo de texto no repositório original](https://github.com/vanish994/DND-projeto-IA/blob/main/Ravenloft_by_J_merged.txt)
5. **Dragon Delves** — [arquivo de texto no repositório original](https://github.com/vanish994/DND-projeto-IA/blob/main/dragon-delves.txt)

Uma cópia local de trabalho dessas fontes pode ser baixada para `biblioteca/fontes/` durante as tarefas de implementação; a pasta está no `.gitignore` e **não deve ser versionada**. Ao transcrever uma regra, registre no código a fonte e a seção (ex.: "Livro do Jogador 2024 — Resistência e Vulnerabilidade").

## Como o agente deve usar a biblioteca

- Consultar as fontes para esclarecer regras e identificar lacunas no Rule Engine.
- Registrar a fonte e a seção relevante para cada conclusão, quando possível.
- Traduzir as conclusões em regras implementáveis e testes automatizados; não tratar o texto do livro como código.
- Preservar o isolamento entre `rule_engine/` e `orchestrator/`; não introduzir dependências da implementação antiga do MJ.
- Preferir materiais com licença aberta ou conteúdo cuja redistribuição esteja autorizada. Não copiar trechos extensos de obras protegidas para documentação, prompts ou testes.

## Inventário de implementação

O estado de cobertura das regras do Livro do Jogador 2024 fica em `RULE_ENGINE.md`, na raiz do repositório. Uma regra só é considerada concluída quando tem implementação, registro no motor, teste determinístico e entrada no inventário.

## Próximo passo

Quando houver autorização adequada para armazenar os arquivos integrais, eles podem ser adicionados aqui. Até lá, este catálogo permite localizar as fontes sem redistribuir seus conteúdos.

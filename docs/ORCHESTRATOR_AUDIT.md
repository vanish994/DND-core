# Auditoria e plano de endurecimento do Orquestrador

## Objetivo

Preparar o Orquestrador para coordenar o Mestre IA e o Rule Engine sem duplicar regras de D&D, preservar o estado da campanha e reduzir o contexto enviado ao modelo. Este documento registra a auditoria inicial e define uma sequência de trabalho incremental; não afirma que funcionalidades planejadas já estejam implementadas.

## Fronteiras arquiteturais

- **Mestre IA:** interpreta a cena, apresenta possibilidades, interpreta NPCs e descreve consequências narrativas. Não decide resultados mecânicos nem controla as ações, pensamentos ou sentimentos do personagem do jogador.
- **Orquestrador:** valida e normaliza intenções estruturadas, verifica pré-condições, escolhe a ferramenta, encaminha fatos confiáveis ao motor, aplica somente alterações confirmadas e monta a resposta compacta para o Mestre.
- **Rule Engine:** autoridade para os resultados mecânicos que implementa. O Orquestrador não deve reproduzir fórmulas nem substituir uma regra ausente por um palpite.
- **Estado da campanha:** fonte autoritativa de fichas, recursos, condições, inimigos e progresso. O bestiário estático fornece blocos de referência; o estado da campanha guarda os valores atuais de cada criatura em cada encontro.

## O que já existe na implementação auditada

- Contratos `Acao` e `ResultadoAcao` em `orchestrator/contratos.py`.
- Entrada principal `OrquestradorAcoes.executar` e adaptador `executar_ferramenta`.
- Preparação de ataques, testes, salvaguardas, características de classe e conjuração.
- Consulta de bestiário e catálogo de armas para evitar aceitar alvos/armas inventados em fluxos já cobertos.
- Aplicação de alterações de estado e consumo de espaços de magia.
- Registro/normalização das rolagens para apresentação.
- Testes unitários e testes de operação composta para magias de área.

A cobertura acima não significa que todo tipo de ação de D&D esteja implementado. O motor e o orquestrador devem recusar explicitamente os casos sem suporte mecânico suficiente.

## Riscos e verificações prioritárias

1. **Fronteira de confiança dos argumentos:** os dados enviados pelo modelo são entrada não confiável. Para cada tipo de ação, definir quais campos são declarativos (intenção, alvo, escolha do jogador) e quais precisam ser recalculados ou recuperados da ficha, do bestiário ou do estado.
2. **Ações não preparadas:** revisar cada tipo encaminhado diretamente a `engine.evaluate`. Uma ação só deve seguir sem preparo se os fatos necessários forem autoritativos ou se a própria regra exigir explicitamente uma rolagem externa.
3. **Estados incompletos:** quando faltar ficha, alvo, CD/CA, recurso ou informação necessária, devolver um bloqueio estruturado com motivo acionável; não inferir valores silenciosamente.
4. **Atomicidade:** validar todos os pré-requisitos antes de gastar recursos ou aplicar efeitos. Uma falha parcial não deve deixar slots, PV, condições ou itens alterados.
5. **Idempotência e efeitos duplicados:** definir como uma mesma solicitação repetida é identificada, principalmente quando houver retries do adaptador ou falhas de rede. Não adicionar um mecanismo de idempotência sem identificar primeiro a fronteira de persistência e o identificador estável da ação.
6. **Estado de combate:** separar dados de referência do monstro (bestiário) de estado da instância no encontro (PV atual, condições, posição, iniciativa). Nunca atualizar apenas o bloco estático do bestiário para representar dano sofrido em campanha.
7. **Contrato de saída para o Mestre:** distinguir `resolvido`, `bloqueado` e eventual estado pendente de informação/rolagem externa. Incluir somente fatos necessários à narração, sem permitir que o Mestre reinterprete o veredito mecânico.
8. **Custo de contexto:** criar uma projeção/resumo do estado relevante para a cena e para a ação atual. Não enviar toda a ficha, todo o bestiário ou todo o histórico em cada chamada por padrão.
9. **Observabilidade:** registrar tipo de ação, resultado, motivo de bloqueio, alterações e identificador de correlação sem guardar segredos ou despejar contexto integral do modelo nos logs.
10. **Compatibilidade:** qualquer novo comportamento deve preservar a API pública atual, salvo migração deliberada e coberta por testes.

## Plano incremental

### Etapa 1 — contrato e mapa de cobertura
- Inventariar todos os tipos de ação aceitos, os campos confiáveis e os pré-requisitos de cada um.
- Mapear quais tipos são preparados pelo Orquestrador, quais vão direto ao motor e por quê.
- Garantir testes de recusa para dados ausentes, tipos desconhecidos e campos mecânicos falsificados.
- Não editar os mesmos arquivos de `rule_engine/` que estão em desenvolvimento paralelo.

### Etapa 2 — validação de entrada
- Normalizar aliases apenas nas fronteiras.
- Validar tipos e estruturas dos argumentos antes de acessar fichas ou chamar o motor.
- Não aceitar modificadores, resultados de dados, CA ou CDs fornecidos pelo modelo quando a fonte autoritativa estiver disponível.
- Para resultados de rolagem externa, representar explicitamente o estado pendente, em vez de assumir sucesso/falha.

### Etapa 3 — transações de estado
- Validar a operação inteira antes de mutações.
- Centralizar a aplicação de alterações confirmadas e tornar cada alteração explícita no resultado.
- Adicionar testes de falha parcial, gasto único e retries. Persistência durável e idempotência distribuída dependem do adaptador/banco que vier a ser usado.

### Etapa 4 — interface do Mestre e economia de tokens
- Definir um contrato pequeno e estável para ferramentas disponíveis ao Mestre.
- Retornar resumos compactos: resultado mecânico, consequências relevantes, alterações de estado e próximo dado necessário.
- Manter a narrativa separada da resolução mecânica; o Mestre pode descrever o resultado, não modificá-lo.
- Testar que resumos omitem dados irrelevantes e nunca substituem a fonte autoritativa.

### Etapa 5 — integração e regressão
- Testar fluxos completos: intenção → validação → motor → estado → resposta ao Mestre.
- Rodar toda a suíte, lint e formatação.
- Integrar com a versão final do Rule Engine por contrato público, sem importar internals desnecessários.

## Critérios de conclusão

- Nenhuma fórmula de D&D duplicada no Orquestrador.
- Nenhum resultado mecânico inventado em caso sem suporte.
- Nenhuma alteração de estado quando uma ação é bloqueada.
- Campos autoritativos não são controlados pelo modelo quando existe uma fonte confiável.
- Repetição/falha de uma chamada não duplica gastos ou efeitos dentro dos limites da arquitetura existente.
- Saída curta, estruturada e suficiente para o Mestre narrar sem recalcular.
- Testes de regressão, lint e formatação aprovados.

## Escopo desta primeira entrega

Esta primeira entrega documenta a arquitetura observada e o plano de auditoria. Ela não altera o comportamento do motor nem declara concluída a integração com um modelo de linguagem ou com uma camada de persistência.

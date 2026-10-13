# Publicar a sala de combate no Render

O repositório inclui um Blueprint em `render.yaml` para executar a sala de combate como um web service Python. O comando de produção usa Gunicorn com um worker, e a persistência remota é obrigatória no serviço publicado.

## Persistência de sessões

- O serviço usa `DATABASE_URL` para PostgreSQL (por exemplo, Neon). Na primeira inicialização, cria a tabela `dnd_core_combat_sessions` se ela ainda não existir.
- A ficha, posições, iniciativa, recursos, condições, log e estado do turno são gravados após cada ação válida e reconstruídos a partir dos catálogos de mapa e bestiário do repositório.
- Sem variáveis de ambiente, a execução local continua usando memória. Para SQLite local, defina `DND_CORE_DATABASE=/caminho/para/sessoes.sqlite3`.
- O Blueprint define `DND_REQUIRE_PERSISTENCE=true`: sem um `DATABASE_URL` válido, o serviço não inicia em modo efêmero por engano.

## Configuração

1. Envie a branch integrada ao GitHub e, no Render, crie um **Blueprint** a partir do repositório.
2. O Render lê `render.yaml` e solicita o valor secreto de `DATABASE_URL` porque está marcado como `sync: false`.
3. Use uma URL de conexão PostgreSQL de um banco dedicado ao jogo. Não coloque a URL em arquivos versionados, PRs, logs ou mensagens públicas.
4. Aguarde o health check `GET /health` e abra `/encontro` na URL `onrender.com` gerada.

A criação/configuração do serviço e do banco deve ser feita depois da autorização do proprietário das contas. O manifesto não cria um banco, não armazena credenciais e não atualiza nenhum plano de cobrança.

## Limitações e segurança

- O plano gratuito do Render suspende o serviço após 15 minutos sem tráfego e a próxima abertura pode levar cerca de um minuto. O banco externo evita perder as partidas quando o processo ou o filesystem efêmero reinicia.
- O plano gratuito não inclui disco persistente local. Para SQLite em hospedagem seria necessário um serviço com disco persistente; este Blueprint usa PostgreSQL para não depender disso.
- Para ficar sempre ativo, seria necessário escolher um plano de computação pago; o projeto não o ativa automaticamente.
- A sala ainda não tem contas de usuário: qualquer pessoa pode iniciar um encontro, e o ID aleatório de 128 bits funciona como credencial de acesso àquela sessão. Trate o link da partida como privado; esta versão é uma demo, não um serviço multiusuário com autenticação.

Consulte também a documentação oficial do [Render Free](https://render.com/docs/free), [discos persistentes](https://render.com/docs/disks), [Blueprint YAML](https://render.com/docs/blueprint-spec) e [deploy Python](https://render.com/docs/deploy-flask).

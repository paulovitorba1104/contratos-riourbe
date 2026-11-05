# Instruções para o Claude neste repositório

## Tudo roda no Docker

Por decisão do dono do projeto, todo trabalho aqui é feito pelo Docker Compose: subir o sistema,
migrações, testes, lint, scripts (`scripts/seed_admin.py`, `scripts/redefinir_senha.py`) e
qualquer validação. Não crie virtualenv, `node_modules` nem PostgreSQL no host para rodar o
projeto. Os comandos estão no README, em "Comandos do dia a dia (tudo pelo Docker)".

- Subir: `docker compose up -d --build` (o backend roda as migrações e o seed ao iniciar). Depois
  de mudar dependências, acrescente `--renew-anon-volumes`: o `node_modules` do frontend é um
  volume anônimo que o Compose reaproveita. Nunca apague `frontend/node_modules` no host com o
  container rodando — é o ponto de montagem desse volume.
- Testes do backend: `docker compose run --rm --no-deps backend sh -c "pip install -q -r requirements-dev.txt && pytest -q"`.
- Frontend: `docker compose exec frontend sh -c "npx tsc --noEmit && npx eslint src"`.
- O `docker-compose.yml` lê `backend/.env` (copiar de `backend/.env.example` se não existir).

A exceção é ferramenta de teste que não faz parte do projeto (ex.: Playwright para testar a tela
no navegador contra `http://localhost:5173`): essa pode rodar no host, num ambiente temporário
fora do repositório.

## Sessões na nuvem do Claude Code

Só vale para o ambiente da nuvem (não para a máquina do usuário), onde o container da sessão
começa do zero:

1. O daemon do Docker não sobe sozinho: `dockerd > /tmp/dockerd.log 2>&1 &` e esperar
   `docker info` responder.
2. O tráfego HTTPS passa por inspeção com uma CA própria do ambiente, que os containers não
   confiam — `pip` e `npm` falham com `CERTIFICATE_VERIFY_FAILED`/`SELF_SIGNED_CERT_IN_CHAIN`.
   Não altere os Dockerfiles do projeto por isso. Recrie localmente as imagens base com a CA,
   mantendo o mesmo nome, e o build do compose passa a usá-las:

   ```bash
   mkdir -p /tmp/base-ca && cp /root/.ccr/ca-bundle.crt /tmp/base-ca/ccr-ca-bundle.crt
   for base in python:3.12-slim node:20-slim; do
     docker pull -q "$base"
     printf 'FROM %s\nCOPY ccr-ca-bundle.crt /usr/local/share/ccr-ca-bundle.crt\nENV SSL_CERT_FILE=/usr/local/share/ccr-ca-bundle.crt PIP_CERT=/usr/local/share/ccr-ca-bundle.crt REQUESTS_CA_BUNDLE=/usr/local/share/ccr-ca-bundle.crt NODE_EXTRA_CA_CERTS=/usr/local/share/ccr-ca-bundle.crt NPM_CONFIG_CAFILE=/usr/local/share/ccr-ca-bundle.crt\n' "$base" > /tmp/base-ca/Dockerfile
     docker build -q --network host -t "$base" /tmp/base-ca
   done
   ```

   Depois disso, `docker compose up -d --build` funciona normalmente. Imagens com `postgres:17`
   são só baixadas, não precisam disso.
3. Se a porta 5432 estiver ocupada, é um PostgreSQL do host: pare-o (`pg_ctlcluster 16 main stop`).

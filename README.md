# Rio-Urbe — Sistema de Gestão de Contratos

Empresa Municipal de Urbanização do Rio de Janeiro (Rio-Urbe) — CNPJ 31.066.178/0001-69
Gerência de Contratos.

Monólito modular: **um backend (FastAPI), um frontend (React)**, com **schemas separados no
PostgreSQL por domínio** (`core`, `contratos`, `faturas`, `licitacao`, `compras`,
`almoxarifado`, `fiscalizacao`, `tarefas`).

Este repositório já passou pela **Fase 0** (infraestrutura base, autenticação/segurança) e está
com o **Módulo Contratos (Fase 1)** em desenvolvimento: entidade Contrato, instrumentos
processuais (aditivos), os 3 relógios de prazo, painel Kanban, fornecedores, modelos RIPM e
atas de registro de preço.

## Stack

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy, Alembic |
| Frontend | React, Vite, TypeScript, Tailwind CSS |
| Banco de dados | PostgreSQL 17 |
| Dev local | Docker Compose |

## Subindo o ambiente com Docker Compose (recomendado)

1. Copie o arquivo de variáveis de ambiente do backend:

   ```bash
   cp backend/.env.example backend/.env
   ```

2. Suba os serviços:

   ```bash
   docker compose up --build
   ```

   Isso vai:
   - subir o PostgreSQL 17 (`db`, porta `5432`)
   - rodar as migrações do Alembic e criar o administrador inicial
   - subir o backend FastAPI em `http://localhost:8000` (com reload)
   - subir o frontend Vite em `http://localhost:5173`

3. Acesse `http://localhost:5173` e entre com as credenciais do `backend/.env`
   (`ADMIN_INICIAL_MATRICULA` / `ADMIN_INICIAL_SENHA`, padrão `admin` / `TrocarSenha#2026`
   em desenvolvimento — **troque em produção**).

4. Documentação interativa da API: `http://localhost:8000/docs`.

## Desenvolvimento local sem Docker (backend)

Requer Python 3.12+ e um PostgreSQL acessível em `127.0.0.1:5432` (ex. via
`docker compose up db`).

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env

alembic upgrade head
python -m scripts.seed_admin

uvicorn app.main:app --reload
```

Rodar os testes:

```bash
pytest
```

## Desenvolvimento local sem Docker (frontend)

Requer Node.js 20+.

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

## Deploy no Railway

Em produção, um **único serviço** builda o `Dockerfile` da raiz do repositório: ele gera o
build do frontend e copia para dentro da imagem do backend, que passa a servir a API (`/api/*`,
`/health`) e a SPA (todo o resto) na mesma origem — evita CORS e problemas de cookie
cross-origin entre dois serviços separados (seção 2 do plano: "monólito modular — um backend,
um deploy"). Os `Dockerfile` dentro de `backend/` e `frontend/` continuam existindo só para o
`docker-compose.yml` de desenvolvimento local (hot reload em processos separados).

Como este repositório precisa da sua conta Railway, os passos abaixo são feitos manualmente no
painel deles (ou via `railway` CLI, se preferir automatizar depois):

1. **Criar o projeto**: no [Railway](https://railway.com/), "New Project" → "Deploy from GitHub
   repo" → selecione `paulovitorba1104/contratos-riourbe`. O Railway detecta o `railway.toml` na
   raiz e builda a partir do `Dockerfile` (também na raiz) automaticamente.

2. **Adicionar o banco**: no mesmo projeto, "New" → "Database" → "PostgreSQL". O Railway cria a
   variável `DATABASE_URL` nesse serviço de banco automaticamente.

3. **Ligar o banco ao serviço web**: nas variáveis de ambiente do serviço web (o que builda o
   `Dockerfile`), adicione `DATABASE_URL` referenciando o serviço de banco, algo como
   `${{Postgres.DATABASE_URL}}` (o Railway sugere essa referência automaticamente ao digitar
   `DATABASE_URL`). Não precisa editar o esquema da URL — o backend normaliza `postgres://`/
   `postgresql://` para o driver `psycopg` usado no projeto.

4. **Configurar as demais variáveis de ambiente** no serviço web (ver `backend/.env.example`
   para a lista completa e a seção 13 do plano para o porquê de cada uma):

   | Variável | Valor em produção |
   |---|---|
   | `AMBIENTE` | `production` |
   | `JWT_SECRET` | gerar com `openssl rand -hex 32` — nunca o valor padrão de dev |
   | `COOKIE_SECURE` | `true` |
   | `ADMIN_INICIAL_MATRICULA` | matrícula do primeiro administrador |
   | `ADMIN_INICIAL_SENHA` | senha forte, diferente do padrão de dev (a guarda de boot recusa subir se for a padrão) |
   | `CORS_ORIGINS` | opcional — como frontend e backend são a mesma origem em produção, só é necessário se algum outro domínio for consumir a API diretamente |

   A guarda de boot (`app/core/boot_guard.py`) recusa o deploy — o processo falha no boot — se
   `JWT_SECRET` for fraco/padrão, `ADMIN_INICIAL_SENHA` for a padrão publicada, ou
   `COOKIE_SECURE` não for `true`. Isso é proposital: é melhor o deploy falhar alto e visível do
   que subir inseguro.

5. **Deploy**: qualquer push na branch configurada dispara um novo deploy. O `CMD` da imagem
   roda `alembic upgrade head` e `python -m scripts.seed_admin` antes de subir o `uvicorn`, então
   migrações e o administrador inicial são aplicados automaticamente a cada deploy (o seed é
   idempotente — só cria o administrador se a matrícula ainda não existir).

6. **Health check**: o Railway usa `GET /health` (configurado em `railway.toml`) para saber se o
   deploy está saudável antes de rotear tráfego para ele.

7. **Domínio**: o Railway gera um domínio `*.up.railway.app` automaticamente; um domínio próprio
   pode ser configurado depois em "Settings → Networking" do serviço.

**Depois do primeiro deploy**, entre com a matrícula/senha do administrador inicial e troque a
senha o quanto antes — este MVP ainda não tem uma tela de troca de senha própria (fica para
antes da Fase 1, é um gap real: hoje só é possível recriar o usuário via `PATCH`/endpoints de
administração).

## Estrutura do repositório

```
backend/
  app/
    core/       # config, segurança (JWT, senha, CPF, rate limit), boot guard
    db/         # engine/sessão SQLAlchemy
    models/     # modelos ORM (schema core: usuarios, log_auditoria)
    schemas/    # schemas Pydantic (entrada/saída da API)
    api/routes/ # rotas FastAPI (auth, usuarios, health)
    middleware/ # headers de segurança, limite de tamanho de corpo
  alembic/      # migrações (cria os schemas dos 7 domínios + tabelas core)
  scripts/      # scripts utilitários (seed do administrador inicial)
  tests/
frontend/
  src/
    pages/      # Login, Hub (blocos dos módulos)
    lib/        # cliente da API, contexto de autenticação
    components/
docker-compose.yml
```

## Segurança implementada nesta fase

Conforme a seção 13 do plano de desenvolvimento:

- Login por matrícula funcional **ou** CPF, com detecção automática de formato e validação de
  dígito verificador do CPF.
- Sessão via JWT único (`{sub, iat, exp}`) em cookie `httpOnly`, `samesite=lax`, `secure` em
  produção, expiração de 12h.
- Revogação server-side de sessão (`sessoes_validas_apos`): logout e troca de senha invalidam
  tokens já emitidos, mesmo antes de expirarem.
- Hash de senha com bcrypt; comparação em tempo constante mesmo para usuário inexistente.
- Política de senha: mínimo 10 caracteres, teto de 72 bytes, mínimo 3 de 4 classes de caractere,
  lista de senhas óbvias proibidas.
- Rate limiting anti-força-bruta em 3 camadas (`ip`, `conta`, `global:login`); sucesso limpa só
  IP e conta — o contador global nunca é limpo.
- RBAC simples: papel global `administrador` x `operador`; proteção contra remover/rebaixar o
  último administrador (HTTP 409).
- Headers de segurança (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, CSP
  restritiva, `Cache-Control: no-store`, HSTS em produção) e limite de tamanho de corpo de
  requisição (1 MiB) aplicados no próprio backend.
- Guarda de boot: a aplicação recusa subir em produção com `JWT_SECRET` fraco/padrão, senha do
  administrador inicial padrão, ou `COOKIE_SECURE` diferente de `true`.
- Handler global de `IntegrityError` → HTTP 409 com mensagem amigável (nunca 500 cru).
- `log_auditoria` (schema `core`) reaproveitável por todos os módulos — quem fez o quê, quando,
  em qual registro.

## Módulo Contratos (Fase 1)

Implementa a seção 4 do plano de desenvolvimento:

- **Contrato**: nasce de 1 forma de contratação (Pregão Eletrônico, Dispensa ou Inexigibilidade);
  status macro (`vigente` → `suspenso` → `encerrado`) só muda através de um instrumento de
  suspensão ou rescisão/extinção — nunca editado diretamente.
- **Instrumentos processuais**: origem + aditivos (prorrogação, acréscimo/supressão de valor,
  alteração qualitativa, reequilíbrio, apostilamento, suspensão, rescisão/extinção), cada um
  mapeado a um modelo RIPM e com fundamentação legal estruturada (lei + artigo).
- **3 relógios de prazo**: vigência atual (derivada do instrumento de origem/prorrogação mais
  recente), teto rígido de 5 anos desde a assinatura original (bloqueia prorrogação que
  ultrapasse — `TetoVigenciaExcedido`), e garantia contratual independente. Alertas calculados
  em 6/3/1 mês (vigência) e 3/1 mês (garantia).
- **Painel Kanban** por status macro, ficha do contrato com timeline de instrumentos, fiscal(is)
  obrigatório(s), fornecedores e atas de registro de preço disponíveis para adesão.
- **Fiscais**: cadastro próprio (`core.fiscais`), independente de usuário do sistema —
  identificado pela matrícula (obrigatória e única), CPF opcional. O vínculo com o contrato é
  temporal (`data_inicio`/`data_fim`), permitindo substituição de fiscal ao longo da vida do
  contrato sem perder o histórico de quem fiscalizou em cada período.
- **Fornecedores**: cadastro próprio (`core.fornecedores`) com validação de CNPJ, mesma lógica
  de cadastro dos fiscais (tela dedicada + criação inline ao criar um contrato).

A tabela `contratos.modelos_ripm` reaproveita o padrão `modelos_checklist`/`conferencias` do
sistema de Faturas, mas fica **vazia até a lista oficial dos 32 modelos RIPM da PGM-Rio ser
fornecida** — é possível cadastrar modelos via `POST /api/modelos-ripm` (restrito a
administrador) enquanto isso.

## Pendências (ver seção 16 do plano)

Itens abaixo **não são bloqueio para a Fase 0**, mas precisam de decisão antes das fases que
dependem deles: e-mail transacional via Brevo (redefinição de senha), provedor de IA, layout
final do hub com Almoxarifado/Fiscalização, entre outros listados no plano de desenvolvimento.

Específico da Fase 1: a lista oficial dos 32 modelos RIPM da PGM-Rio ainda não foi fornecida —
o mecanismo de checklist está pronto, só falta o conteúdo. O relatório anual de Contratos
(estrutura da "planilha de evidências") também está pendente e não foi implementado.

---

Since 2026 — Desenvolvido por Paulo Vitor Barbosa Araújo

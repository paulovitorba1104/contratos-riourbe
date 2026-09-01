# Rio-Urbe — Sistema de Gestão de Contratos

Empresa Municipal de Urbanização do Rio de Janeiro (Rio-Urbe) — CNPJ 31.066.178/0001-69
Gerência de Contratos.

Monólito modular: **um backend (FastAPI), um frontend (React)**, com **schemas separados no
PostgreSQL por domínio** (`core`, `contratos`, `faturas`, `licitacao`, `compras`,
`almoxarifado`, `fiscalizacao`, `tarefas`).

Este repositório está na **Fase 0** do plano de desenvolvimento: infraestrutura base, esqueleto
da aplicação e a fundação de autenticação/segurança sobre a qual os módulos de negócio (Fase 1
em diante) serão construídos.

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

## Pendências (ver seção 16 do plano)

Itens abaixo **não são bloqueio para a Fase 0**, mas precisam de decisão antes das fases que
dependem deles: e-mail transacional via Brevo (redefinição de senha), provedor de IA, layout
final do hub com Almoxarifado/Fiscalização, entre outros listados no plano de desenvolvimento.

---

Since 2026 — Desenvolvido por Paulo Vitor Barbosa Araújo

# Rio-Urbe — Sistema de Gestão de Contratos

Empresa Municipal de Urbanização do Rio de Janeiro (Rio-Urbe) — CNPJ 31.066.178/0001-69
Gerência de Contratos.

Monólito modular: **um backend (FastAPI), um frontend (React)**, com **schemas separados no
PostgreSQL por domínio** (`core`, `contratos`, `faturas`, `licitacao`, `compras`,
`almoxarifado`, `fiscalizacao`, `tarefas`).

Este repositório já passou pela **Fase 0** (infraestrutura base, autenticação/segurança) e tem
dois módulos construídos:

- **Contratos (Fase 1)** — entidade Contrato, instrumentos processuais (aditivos), os 3 relógios
  de prazo, painel Kanban, fiscais, fornecedores, modelos RIPM e atas de registro de preço.
- **Faturamento (Fase 2)** — controle de faturas ligado ao contrato: medição, conferência
  documental por checklist, conferência tributária com alíquotas configuráveis, atesto, glosas e
  painel anual. É ele que alimenta o valor pago do contrato.

## Stack

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy, Alembic |
| Frontend | React, Vite, TypeScript, Tailwind CSS, [lucide-react](https://lucide.dev/) (ícones), fonte Inter self-hosted (`@fontsource/inter`, sem chamada externa) |
| Banco de dados | PostgreSQL 17 |
| Dev local | Docker Compose |

**Fuso horário**: toda contagem de prazo (vigência, garantia, vencimento de fatura) usa o horário
de Brasília explicitamente (`app/core/tempo.py`, `zoneinfo.ZoneInfo("America/Sao_Paulo")`), nunca
o fuso do servidor — containers costumam vir em UTC por padrão (é o caso da imagem base do
Dockerfile), e usar `date.today()` puro contaria o prazo errado nas 3 horas diárias em que UTC já
virou o dia seguinte mas ainda é o dia anterior em Brasília (21h-23h59 horário de Brasília). O
calendário é o gregoriano padrão, por dias corridos (não dias úteis) — é como a vigência
contratual é contada pela Lei 13.303/16 e pela Lei 14.133/21.

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

### Acessando de outros computadores da mesma rede

As portas do `backend` (`8000`) e do `frontend` (`5173`) já ficam expostas para toda a rede
local (não só `127.0.0.1`) — só o `db` (`5432`) continua restrito ao próprio computador, por
segurança. Para outra pessoa no mesmo Wi-Fi/cabo acessar:

1. No computador que está rodando o `docker compose up`, descubra o IP local (Windows:
   `ipconfig` e olhe o "Endereço IPv4" da rede em uso; Linux/Mac: `ip a` ou `ifconfig`).
2. Nos outros computadores, acesse `http://<esse-IP>:5173` no navegador.

As chamadas da API feitas pelo navegador (`/api/...`) passam pelo proxy do Vite
(`frontend/vite.config.ts`) até o backend — por isso não é preciso mexer em `CORS_ORIGINS` nem
em cookies para isso funcionar. Vale o alerta de segurança de sempre: isso deixa o sistema
acessível para qualquer um na mesma rede, então só faz sentido numa rede confiável (ex.: rede
interna do escritório) — nunca exponha essas portas diretamente para a internet.

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
    pages/      # Login, Hub e os módulos (contratos/, faturas/)
    lib/        # cliente da API, contexto de autenticação, navegacao.ts (menu)
    components/ # AppShell + Sidebar (menu lateral, sempre visível) e afins
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

- **Contrato**: identificado por número do contrato + um ou mais números de processo
  administrativo (mínimo 1), cada um marcado com o sistema de origem (SICOP físico,
  Processo.Rio ou SEI.Rio — os 3 sistemas já usados pela Prefeitura) e se é o processo
  principal ou um apenso dele; nasce de 1 forma de
  contratação (Pregão Eletrônico, Dispensa ou Inexigibilidade); status macro
  (`vigente` → `suspenso` → `encerrado`) só muda através de um instrumento de suspensão ou
  rescisão/extinção — nunca editado diretamente. Marca também **quem faz o faturamento**
  (`faturamento_gerido_pela_gct`, padrão verdadeiro): nem todo contrato é faturado pela Gerência
  de Contratos — benefícios são faturados pelo RH, jurídicos pela AJU, por exemplo. Desmarcado
  (com o setor responsável anotado), o contrato sai do módulo de Faturamento — a GCT passa a só
  gerenciar prazo e renovação dele. Ver detalhe do efeito na seção do módulo Faturamento abaixo.
- **Instrumentos processuais**: origem + aditivos (prorrogação, acréscimo/supressão de valor,
  alteração qualitativa, reequilíbrio, apostilamento, suspensão, rescisão/extinção), cada um
  mapeado a um modelo RIPM e com fundamentação legal estruturada (lei + artigo). O instrumento de
  Origem é criado junto com o contrato — a tela "Novo contrato" já pergunta o prazo inicial de
  vigência (início/fim), RIPM e fundamentação; as prorrogações seguintes são registradas depois,
  na ficha do contrato, e só são aceitas até completar o teto de 5 anos contado da assinatura
  original (ex.: 2 anos na contratação inicial + 2 anos + 1 ano de prorrogações = 5 anos).
- **Contador de datas**: no cadastro do contrato (e no formulário de novo instrumento) basta
  informar o início da vigência e o prazo em meses — o sistema devolve o fim da vigência sozinho.
  A contagem inclui o dia de início como primeiro dia de vigência, do jeito que o prazo é escrito
  no contrato: 13/06/2022 por 24 meses termina em **12/06/2024**, a véspera do mesmo dia. O
  cálculo mora no backend (`GET /api/contratos/calcular-vigencia`), usando `relativedelta`, para
  a tela não errar mês de 30/31 dias nem fevereiro (31/01 + 1 mês é 28/02, não 03/03) e para não
  divergir do que é validado ao salvar. O teto de 5 anos continua valendo e é avisado **enquanto
  se digita**: um prazo que ultrapasse o limite mostra a data-limite antes de o usuário tentar
  salvar. A data de fim continua editável, para prazo que não feche em meses redondos. Na ficha
  do contrato, a "Vigência atual" mostra a contagem regressiva legível ("Faltam 8 meses e 12
  dias" / "Vencido há 3 dias").
- **Exceção ao teto de 5 anos (art. 71, I e II, da Lei 13.303/16)**: o teto é a regra, não é
  absoluto — a própria lei prevê duas exceções, e o cadastro/edição do contrato tem um campo para
  registrar qual se aplica: **inciso I** (projeto contemplado no plano de negócios e
  investimentos da empresa) e **inciso II** (o prazo maior é prática rotineira de mercado e
  impor 5 anos inviabilizaria ou oneraria o negócio — o caso típico é locação de imóvel, cujo
  prazo longo é padrão do mercado imobiliário comercial). Marcar a exceção exige justificativa em
  texto e o número do documento que a formaliza (parecer jurídico/SEI) — sem isso o sistema
  recusa, para a exceção não virar uma marcação sem lastro nenhum. Contrato com exceção não tem
  data-limite: nem o contador de datas nem a validação de prorrogação (seção "3 relógios" abaixo)
  bloqueiam por teto — a lei remove o limite nesses casos, não impõe um novo. Na ficha do
  contrato, o card "Vigência atual" mostra "Sem teto de 5 anos — exceção [inciso]" com a
  justificativa e o documento, no lugar da data-limite normal.
- **3 relógios de prazo**: vigência atual (derivada do instrumento de origem/prorrogação mais
  recente), teto rígido de 5 anos desde a assinatura original — salvo exceção registrada, acima —
  (bloqueia prorrogação que ultrapasse — `TetoVigenciaExcedido`), e garantia contratual
  independente. A garantia é um
  histórico de registros (`contratos.garantias_contrato`), nunca sobrescrito — cada alteração
  (definição inicial ou correção) entra como uma linha nova com quem registrou e quando, e a
  garantia "atual" é sempre a mais recente; a tela só mostra os dois campos de data quando o
  usuário clica em "Registrar garantia". Alertas calculados em 6/3/1 mês (vigência) e 3/1 mês
  (garantia) — visíveis tanto na ficha do contrato quanto nos cards do Kanban. Nem todo contrato
  exige garantia (ex.: valor baixo dispensado pela lei) — desmarcando `exige_garantia` (padrão
  verdadeiro) no cadastro/edição, o card de garantia na ficha mostra só "Este contrato não exige
  garantia contratual" (sem o botão de registrar) e o alerta de garantia sai da urgência tanto na
  ficha quanto no Kanban; continua sendo possível registrar garantia mesmo assim se algum dia for
  preciso — a marcação só tira a cobrança, nunca apaga um registro já feito.
- **Reajuste e apostilamento com calculadora embutida**: o contrato marca se tem cláusula de
  reajuste (`tipo_reajuste`: `automatico` — obrigatório, reajusta assim que completa o prazo, sem
  precisar de pedido; ou `mediante_solicitacao` — só se a contratada pedir), a periodicidade em
  meses (normalmente 24) e o índice padrão (ex.: IPCA-E). A ficha mostra o próximo marco do
  reajuste (data de assinatura + periodicidade, ou o último apostilamento de reajuste registrado +
  periodicidade) com o mesmo alerta de 6/3/1 mês da vigência. Ao registrar um apostilamento
  marcado como "é de reajuste", o formulário substitui a calculadora do cidadão: informa-se o
  índice na data-base e o atual, o valor mensal vigente e o período (marco até o próximo marco ou
  o fim da vigência), e o sistema calcula sozinho — mês a mês, convenção de mês comercial de 30
  dias — o valor mensal novo e a diferença a pagar (o valor do apostilamento), mostrando uma
  prévia ao vivo antes de salvar (`GET /api/contratos/calcular-reajuste`). O cálculo final sempre
  roda de novo no backend ao salvar (`POST .../instrumentos`), nunca confia no total calculado no
  navegador. O valor de reajuste/apostilamento entra no `valor_atualizado` do contrato, junto com
  acréscimos e supressões.
- **Anexos nos instrumentos processuais**: cada instrumento (origem, aditivo, apostilamento etc.)
  aceita anexar arquivos (PDF, Word, Excel, imagem — até 25 MB cada) para consulta rápida sem sair
  do sistema — contrato assinado, termo aditivo, parecer, etc. Ficam salvos em disco
  (`backend/uploads/`, fora do controle de versão) e listados na própria linha do instrumento, com
  download/visualização inline e exclusão (restrita a administrador). **Atenção ao ambiente**: com
  Docker Compose local, o bind mount `./backend:/app` faz os arquivos persistirem no disco do
  computador normalmente; num deploy em nuvem com disco efêmero (ex.: Railway, sem volume
  persistente configurado), os arquivos são perdidos a cada redeploy — para uso em produção fora
  do computador local, isso precisa de um volume persistente ou armazenamento externo (S3 e
  equivalentes), ainda não implementado.
- **Contrato por quantidade de execuções**: nem toda dispensa de licitação usa vigência por
  datas. Exemplo real: limpeza de carpete, aplicada um número certo de vezes dentro do mesmo
  exercício (ex.: 3x/ano) — o controle certo é quantidade de execuções previstas × realizadas.
  O contrato marca `modo_execucao = por_quantidade` (padrão continua sendo `por_vigencia`) com a
  `quantidade_execucoes_previstas`; cada aplicação é registrada como uma linha no histórico
  (`contratos.execucoes_contrato`, nunca editado depois — mesmo princípio da garantia), e a
  quantidade realizada é sempre a contagem dessas linhas. A vigência (instrumento de Origem)
  continua sendo informada normalmente — ela ainda limita o exercício —, só deixa de ser o
  critério de conclusão do contrato. Contratos assim normalmente não têm assinatura de
  contrato/termo aditivo: o campo `data_assinatura_original` é reaproveitado como a **data de
  publicação no Diário Oficial** (a tela troca só o rótulo, quando `modo_execucao =
  por_quantidade`), sem precisar de um campo novo nem mexer em `teto_vigencia()`,
  `proximo_marco_reajuste()` ou nas validações que já dependiam dele. Ao atingir a quantidade
  prevista, a ficha mostra um aviso com o atalho "Encerrar contrato" — que abre o formulário de
  novo instrumento já no tipo Rescisão/Extinção — mas o encerramento em si **é sempre decisão de
  quem usa o sistema, nunca automático**: o status só muda quando a pessoa de fato registra esse
  instrumento, o mesmo mecanismo usado para encerrar qualquer outro contrato. Licenças de
  software (pagas por período fixo, sem execução por quantidade) já são atendidas pelo modelo
  padrão — não precisam desse modo.
- **Valor global ou por mensalidade, com calculadora embutida**: a maioria dos contratos já nasce
  com o valor total (global) definido — é o que se digita direto em `valor_inicial`. Alguns (o
  caso típico é locação de imóvel) são cotados por mensalidade: a proposta traz o aluguel mensal,
  o prazo e, às vezes, uma carência (meses de aluguel gratuito no início) — não um valor global
  pronto. O contrato marca `modo_valor` (`global`, padrão, ou `mensal`); no modo mensal,
  informa-se `valor_mensal` e `carencia_meses`, e o `valor_inicial` é **sempre calculado pelo
  backend** — mensalidade × (prazo em meses da vigência do instrumento de Origem − carência),
  nunca aceito pronto do cliente (mesmo racional do valor de reajuste/apostilamento). A tela
  mostra uma prévia ao vivo do valor global antes de salvar
  (`GET /api/contratos/calcular-valor-mensal`), e o cálculo final roda de novo no backend ao
  criar ou editar o contrato.
- **Múltiplos fornecedores no mesmo contrato**: continuando o exemplo da locação de imóvel — é
  comum o contrato ter uma empresa que recebe o aluguel e **outra**, a administradora do prédio,
  que recebe o condomínio (IPTU, taxa condominial, água/luz, taxa de incêndio etc.). Em vez de
  abrir um segundo contrato, o mesmo contrato aceita vincular fornecedores adicionais, cada um com
  um papel em texto livre (ex.: "Administradora do condomínio") — o fornecedor principal
  (`Contrato.fornecedor_id`) continua obrigatório e sem mudança de comportamento para a
  esmagadora maioria dos contratos, que tem só um. Ao lançar uma fatura, escolhe-se a qual
  fornecedor do contrato ela se refere (nulo = fornecedor principal, o padrão); o backend valida
  que só é possível faturar para o principal ou para um dos fornecedores adicionais vinculados a
  esse contrato, nunca para fora desse conjunto.
- **Painel Kanban** por status macro, com número do contrato e alertas de vigência/garantia já
  visíveis no card, busca (número, processo, tipo de serviço ou objeto) e filtro por forma de
  contratação, e um resumo no topo com a contagem de contratos vencidos/vencendo e com garantia
  vencida; ficha do contrato com timeline visual de instrumentos, dados administrativos/
  patrimoniais (nota de reserva/empenho, PT/ND/FR, patrimônio), histórico de alterações
  (auditoria — quem fez o quê e quando), fiscal(is) obrigatório(s), fornecedores e atas de
  registro de preço disponíveis para adesão.
- **Fiscais**: cadastro próprio (`core.fiscais`), independente de usuário do sistema —
  identificado pela matrícula (obrigatória e única), CPF opcional. O vínculo com o contrato é
  temporal (`data_inicio`/`data_fim`), permitindo substituição de fiscal ao longo da vida do
  contrato sem perder o histórico de quem fiscalizou em cada período. "Encerrar vínculo" fecha o
  período mantendo o histórico (substituição); "Excluir" remove o vínculo por completo, para
  quando o fiscal foi designado por engano naquele contrato.
- **Fornecedores**: cadastro próprio (`core.fornecedores`) com validação de CNPJ (dígito
  verificador e situação cadastral ativa na Receita Federal via BrasilAPI), mesma lógica de
  cadastro dos fiscais (tela dedicada, com edição, + criação inline ao criar um contrato). Ao
  digitar os 14 dígitos do CNPJ (nos dois lugares onde se cadastra fornecedor), o sistema já
  consulta a Receita Federal na hora (`GET /api/fornecedores/consulta-cnpj/{cnpj}`) — autopreenche
  a razão social (só quando o campo ainda está vazio, nunca sobrescreve o que a pessoa já digitou)
  e mostra um selo com a situação cadastral. Essa consulta é só prévia visual, de melhor esforço —
  se a API externa estiver fora do ar não bloqueia nada; a verificação que de fato recusa CNPJ
  inativo continua sendo a que roda ao salvar.

A tabela `contratos.modelos_ripm` reaproveita o padrão `modelos_checklist`/`conferencias` do
sistema de Faturas, mas fica **vazia até a lista oficial dos 32 modelos RIPM da PGM-Rio ser
fornecida** — é possível cadastrar modelos via `POST /api/modelos-ripm` (restrito a
administrador) enquanto isso. RIPM é só um checklist de apoio administrativo (a jurídica confere
se cada item da instrução processual foi cumprido) — não é documento jurídico do processo como o
próprio instrumento (origem, apostilamento etc.), então vincular um modelo RIPM ao registrar um
instrumento é **opcional**, nunca obrigatório.

## Módulo Faturamento (Fase 2)

Fecha o ciclo do contrato: é um **controle de faturas** — acompanha e registra o andamento da
nota dentro do processo. A liquidação em si é ato de outro setor, fora deste sistema, então não
existe etapa de liquidação no fluxo; a data é apenas registrada, como já era feito na planilha
de controle.

- **Fluxo por evento registrado**, nunca por edição de status (mesmo princípio do status macro
  do contrato): recebida → conferência → atesto → paga, com **devolvida** e **cancelada** como
  saídas de exceção. Uma nota devolvida pode ser reapresentada como fatura nova apontando para a
  anterior, preservando o rastro.
- **Medição** (`faturas.medicoes`): boletim do período em obras e serviços continuados. O
  contrato marca `exige_medicao`; quando marcado, a fatura só é aceita vinculada a uma medição
  aprovada e ainda não usada por outra nota.
- **Conferência documental**: modelos de checklist configuráveis (`faturas.modelos_checklist`,
  mesmo padrão dos modelos RIPM), preenchidos item a item por fatura como conforme, não conforme
  ou não se aplica. Item marcado como obrigatório trava o atesto enquanto estiver não conforme.
- **Conferência tributária**: para cada tributo, o sistema calcula o **valor esperado** pela
  regra vigente na data de emissão da nota e compara com o **valor informado** na NF, apontando
  divergência. As alíquotas ficam em `faturas.regras_tributarias` — cadastro com alíquota, base
  de cálculo, base legal e vigência, editável pela tela e **entregue vazio**: mudança de
  legislação vira mudança de cadastro, não nova versão do sistema. Nota antiga continua sendo
  conferida pela regra que valia na época dela. Avançar com divergência exige justificativa
  registrada.
- **Glosas** (`faturas.glosas`): abatimento por serviço não prestado, cada uma uma linha nova
  nunca sobrescrita, como o histórico de garantia.
- **Regras que o sistema recusa quebrar**: fatura não ultrapassa o saldo do contrato (valor
  atualizado, com aditivos já contabilizados); só o fiscal com vínculo vigente atesta (ou
  administrador); contrato encerrado não recebe fatura nova; contrato cujo faturamento não é
  gerido pela GCT (`faturamento_gerido_pela_gct = false`) não aceita fatura nenhuma — a tela de
  Nova fatura nem lista esses contratos no seletor.
- **Painel anual**: matriz contrato × mês reproduzindo a aba anual da planilha de controle, mas
  mostrando em que etapa está a fatura de cada competência em vez de só um "X".
- Cada fatura tem o **seu próprio número de processo** (ex.: `006700.000249/2026-51`), que não é
  o processo do contrato, e registra as datas de acompanhamento: recebimento, emissão,
  vencimento, envio à GCO, liquidação e pagamento.

**Integração com Contratos**: o `valor_pago` do contrato é sempre a **soma** de duas partes —
nunca a substituição de uma pela outra:

1. `valor_pago_anterior_sistema` — a parte manual. É para dois casos: um contrato antigo que já
   vem de antes deste sistema (não vale a pena lançar fatura por fatura do histórico — lança-se
   o total já pago de uma vez, no cadastro ou depois pelo box "Valor pago fora do controle de
   faturas deste sistema" na ficha, e o faturamento passa a valer só daqui para frente); ou um
   contrato cujo faturamento é de outro setor (nunca terá fatura no sistema, então essa é a
   única fonte do valor pago, atualizada à mão).
2. O que as faturas **pagas no sistema** já cobrem (soma do valor bruto menos glosas — retenção
   tributária não reduz execução contratual).

Cada fatura paga **soma** à parte manual, nunca a sobrescreve — é o que permite um contrato
antigo entrar no sistema já com saldo, sem que a primeira fatura nova paga apague esse saldo.
A ficha do contrato ganha a seção "Faturas" com a lista daquele contrato (ausente/bloqueada,
com nota explicativa, quando o faturamento não é gerido pela GCT).


## Pendências (ver seção 16 do plano)

Itens abaixo **não são bloqueio para a Fase 0**, mas precisam de decisão antes das fases que
dependem deles: e-mail transacional via Brevo (redefinição de senha), provedor de IA, layout
final do hub com Almoxarifado/Fiscalização, entre outros listados no plano de desenvolvimento.

Específico da Fase 1: a lista oficial dos 32 modelos RIPM da PGM-Rio ainda não foi fornecida —
o mecanismo de checklist está pronto, só falta o conteúdo. O relatório anual de Contratos
(estrutura da "planilha de evidências") também está pendente e não foi implementado.

**Radar CNPJ (planejado, não implementado)**: tela em Contratos com um botão que dispara uma
varredura nos CNPJs de fornecedores já cadastrados, comparando a situação cadastral/dados
atuais na Receita Federal com os dados salvos no sistema — sinalizando quando um fornecedor
mudou algo (ex.: razão social, situação cadastral) sem avisar a Gerência de Contratos. A
verificação de CNPJ ativo ao cadastrar/editar um fornecedor (seção "Fornecedores" acima) já usa
a [BrasilAPI](https://brasilapi.com.br/api/cnpj/v1/{cnpj}) — gratuita, sem necessidade de
chave/autenticação — e o Radar CNPJ reaproveitaria a mesma consulta (`app/core/cnpj_lookup.py`),
rodando-a para todos os fornecedores ativos e comparando o resultado com o cadastro atual.

**Financeiro automatizado via Faturamento (implementado na Fase 2)**: o `valor_pago` do contrato
é alimentado pelas faturas pagas do módulo de Faturamento, mantendo `valor_atualizado` e
`saldo_a_pagar` em dia sem depender de lançamento manual. O atalho "Atualizar valor pago"
continua existindo para os contratos históricos, cujas faturas nunca passaram pelo sistema.

**Alíquotas da conferência tributária (a preencher)**: `faturas.regras_tributarias` é entregue
vazia — enquanto não houver regra cadastrada para um tributo, a conferência daquele imposto não
tem como calcular o esperado e a tela avisa. Cadastrar em Faturas → Configuração as alíquotas,
bases de cálculo e fundamentações que a Rio-Urbe aplica.

**Aviso por e-mail ao fiscal quando a fatura entra (registrado, a implementar)**: toda vez
que uma fatura for gerada/registrada no sistema, o fiscal do contrato recebe um e-mail dizendo
que precisa atestar aquela fatura. Hoje o atesto já existe como evento (`TipoEventoFatura.ATESTO`)
e o vínculo temporal contrato↔fiscal já diz quem é o responsável na data — o que falta é o aviso
sair sozinho, em vez de alguém precisar avisar o fiscal por fora do sistema.

Pré-requisitos e pontos a decidir quando for implementar:

- **O cadastro de fiscal não tem e-mail hoje** (`core.fiscais`: nome, matrícula, CPF, ativo).
  Precisa de campo de e-mail antes de qualquer envio — e de uma decisão sobre o que fazer quando
  o fiscal cadastrado não tiver e-mail preenchido.
- **Envio transacional**: usar o mesmo provedor já previsto nas pendências gerais (Brevo), para
  não haver dois caminhos de e-mail no sistema.
- **Quem recebe**: o(s) fiscal(is) com vínculo aberto no contrato na data da fatura — um contrato
  pode ter mais de um fiscal, e o vínculo é temporal (quem fiscalizava naquele período).
- **Reenvio/cobrança**: definir se o aviso é único (na entrada da fatura) ou se há lembrete
  enquanto a fatura seguir sem atesto, e a partir de quantos dias.
- **Registro do envio**: o e-mail enviado deve ficar registrado (quando, para quem), para o
  processo poder comprovar que o fiscal foi comunicado.

**RIPM em PDF (planejado, não implementado)**: hoje o RIPM é só um cadastro de referência
(`contratos.modelos_ripm`, opcionalmente vinculado a um instrumento). A ideia é o RIPM virar um
formulário preenchível dentro do sistema — a pessoa preenche a instrução processual passo a
passo e o sistema gera um PDF do documento preenchido, como qualquer outro documento de apoio
administrativo do processo (não é documento jurídico do processo em si).

**Timeout de sessão logada (planejado, não implementado)**: hoje a sessão dura o tempo fixo do
JWT (`JWT_EXPIRA_HORAS`, 12h por padrão), sem expirar por inatividade. Fica para ser feito junto
com a tela de "esqueci minha senha"/recuperação de senha (e-mail transacional via Brevo, já
citado nas pendências gerais), já que as duas mexem no mesmo fluxo de autenticação.

**Exclusão de registros**: restrita a administrador (`papel = administrador`) em todos os
cadastros do módulo Contratos — contrato (exclusão em cascata: instrumentos, vínculos de fiscal,
histórico de garantia), fiscal, fornecedor, instrumento processual, ata de registro de preço e
modelo RIPM. Um cadastro referenciado por outro (ex.: fiscal já vinculado a um contrato) não pode
ser excluído — o banco recusa por chave estrangeira e a API devolve 409. O histórico de garantia
(seção acima) e o log de auditoria nunca são excluíveis — são registros de auditoria por
definição.

**Verificação automática de completude/conformidade (planejado, não implementado)**: treinar a
ferramenta para identificar sozinha quando falta algo em um contrato ou quando algum item
obrigatório não foi cumprido (ex.: fundamentação legal incompleta, instrumento sem documento SEI,
prazo/fiscal/garantia pendente, dado que a lei ou a modalidade de contratação exige e não foi
preenchido) — hoje a checagem é toda manual, feita por quem está com o processo. A ideia não é
específica do módulo Contratos: deve ser levada para todas as modalidades/módulos do sistema
(Licitação, Faturas, Diárias/Passagens/Compras etc.) conforme forem sendo construídos.

**Módulo Fiscalização — fiscalização contratual completa e automatizada (registrado, a
detalhar)**: ideia anotada para quando o módulo Fiscalização for construído. Hoje esse
acompanhamento é todo manual e vive fora do sistema. O que o módulo precisa cobrir:

- **Acompanhamento das empresas contratadas**: verificar se estão pagando corretamente e se a
  documentação está em dia — regularidade que precisa ser conferida de forma recorrente, não só
  na contratação.
- **Obrigações do contrato, dos dois lados**: hoje é preciso ler o contrato para saber quais são
  as obrigações da contratada e quais são as da Rio-Urbe. O módulo precisa ter essas obrigações
  registradas e acompanháveis, em vez de depender de alguém reler o contrato a cada vez.
- **Sinalização de descumprimento**: o sistema deve avisar sempre que uma empresa estiver
  descumprindo regra contratual — o alerta é o produto principal do módulo, não um extra.
- **Automatização**: a premissa é que tudo isso seja automatizado ao máximo; checagem manual é
  exatamente o que o módulo existe para substituir.

Conecta diretamente com a "verificação automática de completude/conformidade" registrada acima —
é a mesma ideia aplicada à execução do contrato (a empresa está cumprindo?), enquanto aquela
olha a formação do processo (falta algum item?).

**Pendente de insumo**: um **manual de fiscalização** será fornecido quando o assunto for
retomado. Ele é a base para o desenho do módulo — a modelagem (que obrigações existem, com que
periodicidade são checadas, quais documentos comprovam cada uma, o que caracteriza descumprimento
e qual a providência) deve sair dele, não de suposição. Também fica para essa conversa definir o
que exatamente entra em "pagando certinho" (encargos trabalhistas e previdenciários da mão de
obra alocada, regularidade fiscal, ou ambos).

**Módulo Almoxarifado — compras avulsas com faturamento, mas sem ser "contrato" (registrado, a
detalhar)**: existem compras (ex.: material de almoxarifado) que são entrega de produto, não
serviço continuado — não fazem sentido no módulo Contratos, mas precisam de faturamento mesmo
assim, e hoje esse faturamento não tem onde entrar no sistema. O Almoxarifado ainda vai ser
estruturado (é um módulo do hub ainda não construído); quando for, ele precisa nascer já ligado
ao módulo Faturamento — do jeito que o próprio Faturamento hoje é alimentado pelo módulo
Contratos (fatura aponta para um contrato), uma compra de almoxarifado vai precisar poder
alimentar uma fatura sem que exista um contrato por trás dela. Vale revisitar, nessa hora, se o
`contrato_id` obrigatório em `faturas.faturas` precisa virar opcional (ou se o Almoxarifado gera
algum registro equivalente a "contrato" só para a fatura apontar) — decisão de desenho a tomar
quando o módulo Almoxarifado for desenhado, não antes.

**Consulta de jurisprudência do TCM-RJ e do TCU (agendado, a pesquisar)**: buscar uma API que
permita consultar jurisprudência dos dois tribunais de contas sobre licitações e contratos, para
o sistema poder trazer os precedentes relevantes ao lado do caso concreto — hoje essa pesquisa é
feita manualmente, fora do sistema.

O primeiro passo é levantamento, não implementação: descobrir o que cada tribunal expõe.

- **TCU** — verificar o portal de dados abertos e a Pesquisa Integrada: se há endpoint público de
  acórdãos e jurisprudência selecionada, qual o formato de resposta, se exige credencial e quais
  os limites de uso.
- **TCM-RJ** — verificar se existe API ou só consulta pelo site. Não havendo API, avaliar as
  alternativas (raspagem responsável dentro dos termos de uso, base própria alimentada por
  importação periódica, ou nenhuma integração automática).

Definido o que existe, decidir o encaixe no sistema: onde a consulta aparece (provavelmente na
análise processual do contrato e na Licitação), se os resultados ficam em cache local para não
depender do tribunal estar no ar, e como citar a fonte e a data da consulta — jurisprudência muda,
e um parecer precisa registrar em que precedente se apoiou e quando.

---

Since 2026 — Desenvolvido por Paulo Vitor Barbosa Araújo

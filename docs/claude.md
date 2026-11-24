# claude.md: instruções para a IA

> Este arquivo é o "cérebro" do projeto para assistentes de IA (Claude, Copilot, Cursor).
> **Leia antes de gerar qualquer código.** Em caso de conflito, `docs/architecture.md` e este arquivo vencem.

## 1. Contexto

SUS Connect é um projeto **educacional** (Build to Learn) inspirado no Prontuário Único do SUS. Não é um sistema real e nunca deve conter dados reais de pacientes. A prioridade é **aprendizado**: prefira código claro e explicável a código "esperto".

A arquitetura é **API-first**: a API é o produto e o `apps/web` é apenas o primeiro cliente (profissionais). No futuro, novos clientes (portal do paciente, app) consumirão a mesma API. Por isso o contrato `/api/v1` deve ser estável e **nenhuma regra de negócio ou de permissão pode viver só no frontend**.

## 2. Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic, PostgreSQL 16, PyJWT, argon2-cffi
- **Frontend:** Next.js 14 (App Router), TypeScript, Tailwind CSS, React Query
- **Testes:** pytest (backend), Playwright (E2E)
- **Infra:** Docker, Docker Compose, GitHub Actions
- **Estrutura:** monorepo (`apps/api`, `apps/web`, `packages`, `docs`, `tests`, `docker`)

## 3. Arquitetura

Clean Architecture em quatro camadas dentro de `apps/api/app/`:

```
domain/          → entidades, value objects, regras de negócio, interfaces de repositório
application/     → casos de uso
infrastructure/  → SQLAlchemy, armazenamento de arquivos, Alembic, segurança (Argon2, JWT)
api/             → routers FastAPI, schemas Pydantic, dependências
```

**Regras de dependência (inegociáveis):**
- `domain` **não importa** FastAPI, SQLAlchemy, Pydantic nem nada de infraestrutura.
- `application` importa apenas `domain`.
- Routers **não contêm regra de negócio**: só traduzem HTTP ↔ caso de uso.
- Acesso a banco só via repositórios (interfaces no domínio, implementação na infraestrutura).

> Até o Dia 4 a estrutura pode ser mais plana. A separação em camadas é feita na refatoração do Dia 5. Nunca antecipe abstração sem teste pedindo por ela.

## 4. Fluxo de trabalho (TDD)

1. **Red:** escreva o teste que descreve **um** comportamento e veja ele falhar.
2. **Green:** escreva o **mínimo** de código para passar.
3. **Refactor:** limpe sem mudar comportamento, com os testes verdes.

Regras: um teste = um comportamento. Nomes descritivos (`test_register_patient_with_duplicate_cpf_fails`). Nunca altere um teste só para fazê-lo passar. Nunca escreva código de produção sem teste que o exija. Para **toda rota protegida**, escreva no mínimo três testes: sem token (401), papel sem permissão (403) e papel correto (sucesso). Os testes ficam em `apps/api/tests` (API como caixa-preta, via `TestClient`, banco `<db>_test`), com as fixtures `admin`, `doctor`, `receptionist` e os payloads de `tests/factories.py`. O E2E (Playwright) fica em `tests/`, na raiz. Códigos de status, paginação e formato de erro estão em `architecture.md`, seção 9; a estratégia de testes, na seção 13.

## 5. Regras de negócio

**Autenticação e autorização**
- Toda rota exige usuário autenticado, exceto `/api/v1/auth/login`, `/api/v1/auth/refresh` e `/health*`. **Negar por padrão.**
- Login por e-mail + senha → access token JWT (15 min) + refresh token opaco (7 dias, guardado como hash SHA-256, com rotação; reuso de refresh antigo revoga a família inteira).
- Senhas: Argon2id, mínimo de 10 caracteres. Nunca logar nem retornar senha, hash ou token.
- 5 falhas seguidas bloqueiam a conta por 15 minutos. O login responde sempre `401 Invalid credentials` para e-mail inexistente, senha errada **e** conta bloqueada.
- Papéis: `ADMIN`, `DOCTOR`, `RECEPTIONIST`. A matriz oficial está em `architecture.md` (seção 7). **ADMIN não acessa dados clínicos.**
- Não existe autocadastro: só `ADMIN` cria usuários. Usuário `DOCTOR` é vinculado a um `Doctor`.
- Médico só registra prontuário e prescreve nos **próprios** atendimentos.
- O primeiro `ADMIN` é criado por comando de seed e deve trocar a senha no primeiro acesso.

**Paciente**
- CPF obrigatório, único e com dígitos verificadores válidos. CPF não pode ser alterado depois.
- CNS opcional, com 15 dígitos.
- Data de nascimento não pode ser futura.
- `DELETE /patients/{id}` **desativa** (`active = false`); nunca apaga fisicamente.
- Paciente desativado não pode receber novos atendimentos, mas o histórico permanece consultável.
- O CPF de um paciente desativado continua **reservado** (novo cadastro com o mesmo CPF → `409`). Reativar é um caso de uso próprio (`POST /patients/{id}/reactivate`).

**Profissional (Doctor)**
- Par `license_number` + `license_state` único. Desativação é soft delete.

**Atendimento**
- Exige paciente **e** médico ativos.
- Status: `SCHEDULED` → `COMPLETED` ou `CANCELLED`. Só é editável enquanto `SCHEDULED`. `COMPLETED` não pode ser cancelado.
- Concluir exige um MedicalRecord.

**MedicalRecord**
- Um por atendimento. **Append-only:** correções viram adendos, nunca edição do original.

**Prescrição**
- Pertence a um atendimento; só o médico daquele atendimento pode emiti-la. Tem 1+ itens.

**Exame**
- Aceita PDF, PNG, JPG até 10 MB. O arquivo vai para o `FileStorage`; no banco ficam só metadados e SHA-256.

**Vacina**
- Data de aplicação não pode ser futura.

**Auditoria (AuditLog)**
- Todo acesso (inclusive **leitura**) a dado de paciente gera registro: quem, quando, o quê, qual paciente, IP.
- O ator vem **sempre do token validado**, nunca de header ou corpo da requisição. Também registra `LOGIN_SUCCESS`, `LOGIN_FAILED`, `LOGOUT` e `ACCESS_DENIED`.
- **Cronograma:** a gravação do AuditLog entra no Dia 5 (teste primeiro). Antes disso, não implemente nem teste auditoria.
- Append-only: nunca atualizar nem apagar.

## 6. Convenções de código

**Gerais**
- Código, nomes de classes/funções/variáveis, commits e comentários técnicos em **inglês**.
- Textos de interface, mensagens ao usuário e documentação em **português (pt-BR)**.
- Commits no padrão Conventional Commits: `feat:`, `fix:`, `test:`, `refactor:`, `docs:`, `chore:`.

**Python**
- Type hints em tudo. Funções curtas, com uma responsabilidade.
- `snake_case` para funções e variáveis, `PascalCase` para classes.
- Entidades de domínio são classes simples (dataclasses), sem dependência de ORM.
- Exceções de domínio próprias (`InvalidCpfError`, `PatientNotFoundError`), traduzidas para HTTP na camada `api`.
- Schemas Pydantic ficam em `api/`, nunca no domínio.
- Todas as rotas de negócio ficam sob o prefixo **`/api/v1`**; só `/health*` fica fora. Os testes já usam esse caminho.
- Toda listagem é **paginada** (`limit` e `offset`) e devolve `{items, total, limit, offset}`.
- Datas e horas sempre em **UTC**, ISO 8601 com fuso explícito (datetime sem fuso → `422`). A conversão para o fuso local é só na exibição.
- Status HTTP e erros seguem `architecture.md`, seção 9 (`409` para duplicidade e regra de estado, `422` para validação).

**TypeScript / Next.js**
- `strict` ligado; sem `any`.
- Server Components por padrão; `"use client"` só quando houver interatividade.
- Dados do servidor via React Query; sem `fetch` espalhado em componentes.
- Tokens ficam em cookies `httpOnly` gerenciados pelo servidor Next.js (padrão BFF). **Nunca** em `localStorage`/`sessionStorage` nem acessíveis ao JavaScript do navegador.
- Componentes em `PascalCase`, arquivos de rota seguem o App Router.

**Banco**
- Toda mudança de schema via **migração Alembic**; nunca editar tabela na mão.
- Tabelas em `snake_case` e plural (`patients`, `appointments`).
- Chaves primárias UUID. Colunas `created_at` e `updated_at` em todas as tabelas.

## 7. Segurança (LGPD)

- Dados de saúde são sensíveis. **Apenas dados fictícios** em desenvolvimento e testes.
- Nunca colocar segredos no código ou no git; usar variáveis de ambiente (`.env` fora do repositório).
- Nunca logar CPF, CNS ou conteúdo clínico.
- Mensagens de erro não devem expor dados de pacientes.
- Validar toda entrada na borda da API.
- Segredos de auth (`JWT_SECRET`, senha do admin) só em variáveis de ambiente; nunca fixos no código.
- Toda rota declara a autenticação e a permissão exigidas; rota sem declaração é bug.

## 8. O que a IA NÃO deve fazer

- Gerar código sem teste correspondente. No **Dia 3** só se escrevem testes, nenhum código de produção.
- Pular camadas (router acessando banco direto).
- Adicionar bibliotecas ou dependências sem justificar.
- Fazer exclusão física de dados clínicos.
- Reescrever grandes partes do projeto sem pedido explícito.
- Colocar regra de negócio ou de permissão apenas no frontend.
- Implementar itens da **Fase 2** (papel `PATIENT`, rotas `/me/...`, rate limiting, gov.br) sem pedido explícito; ver `architecture.md`, seção 12.
- Criar rota sem dependência de autenticação e permissão.
- Confiar em identidade ou papel enviados pelo cliente (header, corpo, query).
- Guardar senha ou refresh token em texto puro, ou token no `localStorage`.
- Inventar regras de negócio que não estejam neste arquivo ou em `architecture.md`. Em caso de dúvida, **perguntar**.

## 9. Como a IA deve responder

- Explique o **porquê** das decisões (o objetivo é aprender).
- Mostre mudanças pequenas e revisáveis, uma de cada vez.
- Aponte trade-offs quando houver mais de um caminho.

## 10. Comandos úteis

```bash
docker compose up --build        # sobe tudo
docker compose logs -f api       # logs da API
docker compose exec api pytest   # roda os testes (a partir do Dia 3)
docker compose exec api python -m app.cli create-admin   # cria o primeiro ADMIN (a partir do Dia 4)
docker compose down -v           # derruba tudo e apaga o banco
```

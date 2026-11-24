# SUS Connect

## Objetivo

Sistema educacional inspirado no conceito de Prontuário Único do SUS.

Este projeto tem como objetivo estudar:

- Arquitetura de Software
- Engenharia Assistida por IA
- Clean Architecture
- TDD
- FastAPI
- Next.js
- PostgreSQL
- Docker
- CI/CD

## Funcionalidades

- Cadastro de pacientes
- Cadastro de profissionais
- Registro de atendimentos
- Registro de exames
- Registro de vacinas
- Registro de prescrições
- Autenticação e controle de acesso por papéis (JWT + RBAC)
- Auditoria de acessos

## Stack

### Backend

- Python
- FastAPI
- PostgreSQL
- JWT + Argon2 (autenticação)

### Frontend

- Next.js
- TypeScript
- TailwindCSS

### Infraestrutura

- Docker
- Docker Compose

## Objetivo de Aprendizado

Build to Learn.

A prioridade deste projeto é aprendizado e evolução técnica.

## Estrutura

```
sus-connect/
├── apps/
│   ├── api/       # FastAPI (testes em apps/api/tests)
│   └── web/       # Next.js
├── packages/      # código compartilhado (futuro)
├── docs/          # arquitetura e documentação
├── tests/         # testes de ponta a ponta
├── docker/        # arquivos auxiliares de infra
├── docker-compose.yml
└── .env.example
```

## Como rodar

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: http://localhost:3000
- API: http://localhost:8000
- Docs da API (Swagger): http://localhost:8000/docs
- Health check: http://localhost:8000/health
- Health check do banco: http://localhost:8000/health/db

Para parar: `docker compose down` (use `-v` para apagar também o volume do banco).

## Roadmap

- [x] Dia 1: Engenharia do projeto (ambiente Docker)
- [x] Dia 2: Arquitetura e docs (`docs/architecture.md`, `docs/claude.md`)
- [x] Dia 3: TDD (testes falhando, incluindo autenticação e autorização)
- [ ] Dia 4: Backend (inclui autenticação JWT + RBAC)
- [ ] Dia 5: Refatoração e AuditLog
- [ ] Dia 6: Frontend (inclui login)
- [ ] Dia 7: CI/CD e deploy

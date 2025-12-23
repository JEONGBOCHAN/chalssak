# Azure 배포 가이드

## 개요

Docuchat 프로젝트를 Azure에 Docker 기반으로 배포하기 위한 가이드입니다.

## 배포 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                         Azure                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Container Apps Environment              │   │
│  │  ┌─────────────────┐    ┌─────────────────┐        │   │
│  │  │    Frontend     │    │    Backend      │        │   │
│  │  │   (Next.js)     │───▶│   (FastAPI)     │        │   │
│  │  │   Port 3000     │    │   Port 8000     │        │   │
│  │  └─────────────────┘    └────────┬────────┘        │   │
│  └──────────────────────────────────┼──────────────────┘   │
│                                     │                       │
│  ┌──────────────────────────────────▼──────────────────┐   │
│  │           Azure Database for PostgreSQL              │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Azure Container Registry                 │   │
│  │    docuchat.azurecr.io/frontend:latest               │   │
│  │    docuchat.azurecr.io/backend:latest                │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   Google AI     │
                    │  (Gemini API)   │
                    └─────────────────┘
```

## 사전 요구사항

### 필수

- Azure 계정 및 활성 구독
- Azure CLI 설치 (`az` 명령어)
- Docker Desktop 설치
- Git

### 선택

- GitHub 계정 (CI/CD 구성 시)
- 커스텀 도메인 (선택)

## Azure 리소스

### 리소스 그룹

| 리소스 | 이름 (예시) | SKU/Tier | 예상 월 비용 |
|--------|-------------|----------|--------------|
| Resource Group | rg-docuchat | - | 무료 |
| Container Registry | docuchat | Basic | ~$5 |
| Container Apps Environment | cae-docuchat | Consumption | 사용량 기반 |
| Container App (Backend) | ca-backend | - | ~$10-20 |
| Container App (Frontend) | ca-frontend | - | ~$5-10 |
| PostgreSQL Flexible Server | psql-docuchat | Burstable B1ms | ~$15 |

**예상 총 비용: $35-50/월** (트래픽에 따라 변동)

## Docker 구성

### 현재 상태

| 컴포넌트 | Dockerfile | 상태 |
|----------|------------|------|
| Backend | `Dockerfile` | ✅ 있음 |
| Frontend | `frontend/Dockerfile` | ❌ 없음 (작성 필요) |

### 백엔드 Dockerfile 구조

```dockerfile
# Multi-stage build
FROM python:3.12-slim as builder
# 의존성 설치

FROM python:3.12-slim as production
# 프로덕션 실행
EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 프론트엔드 Dockerfile (작성 예정)

```dockerfile
# Multi-stage build
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
```

### docker-compose 구성

```yaml
version: "3.9"

services:
  backend:
    build:
      context: .
      target: production
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/docuchat
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
    depends_on:
      - db

  frontend:
    build:
      context: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000
    depends_on:
      - backend

  db:
    image: postgres:16-alpine
    environment:
      - POSTGRES_USER=docuchat
      - POSTGRES_PASSWORD=docuchat
      - POSTGRES_DB=docuchat
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## 환경 변수

### 백엔드

| 변수명 | 설명 | 예시 |
|--------|------|------|
| `GOOGLE_API_KEY` | Gemini API 키 | `AIzaSy...` |
| `DATABASE_URL` | PostgreSQL 연결 문자열 | `postgresql://user:pass@host:5432/db` |
| `APP_ENV` | 환경 구분 | `production` |
| `CORS_ORIGINS` | 허용 도메인 | `https://frontend.azurecontainerapps.io` |

### 프론트엔드

| 변수명 | 설명 | 예시 |
|--------|------|------|
| `NEXT_PUBLIC_API_URL` | 백엔드 API URL | `https://backend.azurecontainerapps.io` |

## 배포 단계

### Phase 1: 로컬 Docker 환경 구성

1. **프론트엔드 Dockerfile 작성**
   ```bash
   # frontend/Dockerfile 생성
   # frontend/.dockerignore 생성
   ```

2. **docker-compose 통합**
   ```bash
   # 로컬에서 전체 스택 테스트
   docker-compose up --build
   ```

3. **PostgreSQL 마이그레이션**
   ```bash
   # SQLite → PostgreSQL 전환
   # 로컬 PostgreSQL 컨테이너로 테스트
   ```

### Phase 2: Azure 리소스 생성

1. **리소스 그룹 생성**
   ```bash
   az group create --name rg-docuchat --location koreacentral
   ```

2. **Container Registry 생성**
   ```bash
   az acr create --name docuchat --resource-group rg-docuchat --sku Basic
   az acr login --name docuchat
   ```

3. **PostgreSQL 생성**
   ```bash
   az postgres flexible-server create \
     --name psql-docuchat \
     --resource-group rg-docuchat \
     --location koreacentral \
     --admin-user adminuser \
     --admin-password <password> \
     --sku-name Standard_B1ms \
     --tier Burstable
   ```

4. **Container Apps Environment 생성**
   ```bash
   az containerapp env create \
     --name cae-docuchat \
     --resource-group rg-docuchat \
     --location koreacentral
   ```

### Phase 3: 이미지 빌드 및 푸시

1. **이미지 빌드**
   ```bash
   # 백엔드
   docker build -t docuchat.azurecr.io/backend:latest .

   # 프론트엔드
   docker build -t docuchat.azurecr.io/frontend:latest ./frontend
   ```

2. **이미지 푸시**
   ```bash
   docker push docuchat.azurecr.io/backend:latest
   docker push docuchat.azurecr.io/frontend:latest
   ```

### Phase 4: Container Apps 배포

1. **백엔드 배포**
   ```bash
   az containerapp create \
     --name ca-backend \
     --resource-group rg-docuchat \
     --environment cae-docuchat \
     --image docuchat.azurecr.io/backend:latest \
     --target-port 8000 \
     --ingress external \
     --registry-server docuchat.azurecr.io \
     --env-vars GOOGLE_API_KEY=<key> DATABASE_URL=<url>
   ```

2. **프론트엔드 배포**
   ```bash
   az containerapp create \
     --name ca-frontend \
     --resource-group rg-docuchat \
     --environment cae-docuchat \
     --image docuchat.azurecr.io/frontend:latest \
     --target-port 3000 \
     --ingress external \
     --registry-server docuchat.azurecr.io \
     --env-vars NEXT_PUBLIC_API_URL=https://ca-backend.<env>.azurecontainerapps.io
   ```

### Phase 5: CI/CD 구성

`.github/workflows/deploy.yml` 생성:

```yaml
name: Deploy to Azure

on:
  push:
    branches: [master]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Login to Azure
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Login to ACR
        run: az acr login --name docuchat

      - name: Build and push backend
        run: |
          docker build -t docuchat.azurecr.io/backend:${{ github.sha }} .
          docker push docuchat.azurecr.io/backend:${{ github.sha }}

      - name: Build and push frontend
        run: |
          docker build -t docuchat.azurecr.io/frontend:${{ github.sha }} ./frontend
          docker push docuchat.azurecr.io/frontend:${{ github.sha }}

      - name: Deploy to Container Apps
        run: |
          az containerapp update --name ca-backend --resource-group rg-docuchat \
            --image docuchat.azurecr.io/backend:${{ github.sha }}
          az containerapp update --name ca-frontend --resource-group rg-docuchat \
            --image docuchat.azurecr.io/frontend:${{ github.sha }}
```

## 보안 고려사항

### 시크릿 관리

- Azure Key Vault 사용 권장
- GitHub Secrets에 민감 정보 저장
- 환경 변수로 API 키 전달 (하드코딩 금지)

### 네트워크

- Container Apps 내부 통신은 private
- PostgreSQL은 Azure 내부에서만 접근 가능하도록 설정
- HTTPS 강제 (Ingress 설정)

### CORS

```python
# src/core/config.py
CORS_ORIGINS = [
    "https://ca-frontend.<env>.azurecontainerapps.io",
    # 커스텀 도메인 추가
]
```

## 모니터링

### Azure Monitor

- Container Apps 기본 메트릭 제공
- Log Analytics Workspace 연동

### 헬스체크

- 백엔드: `GET /api/v1/health`
- 프론트엔드: Next.js 기본 헬스체크

## 트러블슈팅

### 자주 발생하는 문제

| 문제 | 원인 | 해결 |
|------|------|------|
| 이미지 푸시 실패 | ACR 로그인 만료 | `az acr login --name docuchat` |
| 컨테이너 시작 실패 | 환경 변수 누락 | Container App 환경 변수 확인 |
| DB 연결 실패 | 방화벽 규칙 | PostgreSQL 방화벽에 Container Apps IP 추가 |
| CORS 오류 | 도메인 미등록 | CORS_ORIGINS에 프론트엔드 도메인 추가 |

### 로그 확인

```bash
# Container App 로그
az containerapp logs show --name ca-backend --resource-group rg-docuchat

# 실시간 로그 스트리밍
az containerapp logs show --name ca-backend --resource-group rg-docuchat --follow
```

## 관련 문서

- [Azure ACR 설정](./azure-acr-setup_kr.md)
- [Azure Container Apps 설정](./azure-container-apps-setup_kr.md)

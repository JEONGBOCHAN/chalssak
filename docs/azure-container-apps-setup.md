# Azure Container Apps 배포 가이드

> 작성일: 2025-12-21
> 관련 이슈: CHA-69
> 선행 작업: [Azure Container Registry 설정](./azure-acr-setup.md) (CHA-68)

## 목차

1. [개요](#1-개요)
2. [사전 요구사항](#2-사전-요구사항)
3. [Container Apps 환경 생성](#3-container-apps-환경-생성)
4. [Azure Database for PostgreSQL 설정](#4-azure-database-for-postgresql-설정)
5. [백엔드 Container App 배포](#5-백엔드-container-app-배포)
6. [프론트엔드 Container App 배포](#6-프론트엔드-container-app-배포)
7. [환경 변수 및 시크릿 설정](#7-환경-변수-및-시크릿-설정)
8. [Ingress 및 외부 접근 설정](#8-ingress-및-외부-접근-설정)
9. [Health Probes 설정](#9-health-probes-설정)
10. [스케일링 설정](#10-스케일링-설정)
11. [Azure Portal 사용 방법](#11-azure-portal-사용-방법)
12. [비용 추정](#12-비용-추정)
13. [트러블슈팅](#13-트러블슈팅)

---

## 1. 개요

### Azure Container Apps란?

Azure Container Apps는 서버리스 컨테이너 플랫폼으로, Kubernetes의 복잡성 없이 컨테이너화된 애플리케이션을 실행할 수 있습니다.

### 아키텍처

```
                    ┌─────────────────────────────────────────────┐
                    │       Azure Container Apps Environment      │
                    │              (cae-docuchat)                 │
                    │                                             │
┌─────────┐        │  ┌─────────────────┐  ┌─────────────────┐  │        ┌─────────────────┐
│ 사용자   │───────▶│  │ Frontend App    │  │ Backend App     │──│──────▶ │ PostgreSQL      │
│         │        │  │ (ca-docuchat-   │  │ (ca-docuchat-   │  │        │ Flexible Server │
│         │◀───────│  │  frontend)      │──│  backend)       │  │        │                 │
└─────────┘        │  │ Port: 3000      │  │ Port: 8000      │  │        └─────────────────┘
                    │  └─────────────────┘  └─────────────────┘  │
                    │                                             │
                    └─────────────────────────────────────────────┘
                                        │
                                        ▼
                              ┌─────────────────┐
                              │ Azure Container │
                              │ Registry (ACR)  │
                              │ docuchat.       │
                              │ azurecr.io      │
                              └─────────────────┘
```

### 리소스 명명 규칙

| 리소스 유형 | 이름 | 설명 |
|------------|------|------|
| 리소스 그룹 | `rg-docuchat` | 모든 리소스 그룹화 |
| Container Apps 환경 | `cae-docuchat` | 컨테이너 앱 실행 환경 |
| 백엔드 앱 | `ca-docuchat-backend` | FastAPI 백엔드 |
| 프론트엔드 앱 | `ca-docuchat-frontend` | Next.js 프론트엔드 |
| PostgreSQL 서버 | `psql-docuchat` | 데이터베이스 서버 |
| Log Analytics | `log-docuchat` | 로그 수집 |

---

## 2. 사전 요구사항

### 필수 항목

| 항목 | 설명 | 확인 방법 |
|------|------|----------|
| Azure 구독 | 활성 Azure 구독 | Azure Portal 로그인 후 확인 |
| Azure CLI | v2.50.0 이상 | `az --version` |
| ACR 설정 완료 | CHA-68 완료 | `az acr show --name docuchat` |
| Docker 이미지 | ACR에 푸시됨 | `az acr repository list --name docuchat` |

### Azure CLI 확장 설치

```bash
# Container Apps 확장 설치
az extension add --name containerapp --upgrade

# 확장 설치 확인
az extension list --query "[?name=='containerapp']" --output table
```

### 리소스 공급자 등록

```bash
# Container Apps 리소스 공급자 등록
az provider register --namespace Microsoft.App

# 운영 인사이트 리소스 공급자 등록
az provider register --namespace Microsoft.OperationalInsights

# 등록 상태 확인
az provider show --namespace Microsoft.App --query "registrationState"
az provider show --namespace Microsoft.OperationalInsights --query "registrationState"
```

---

## 3. Container Apps 환경 생성

Container Apps 환경은 여러 Container App이 공유하는 보안 경계입니다.

### 3.1 변수 설정

```bash
# 공통 변수
RESOURCE_GROUP="rg-docuchat"
LOCATION="koreacentral"
ENVIRONMENT_NAME="cae-docuchat"
LOG_ANALYTICS_WORKSPACE="log-docuchat"
ACR_NAME="docuchat"
```

### 3.2 Log Analytics 워크스페이스 생성

```bash
# Log Analytics 워크스페이스 생성
az monitor log-analytics workspace create \
  --resource-group $RESOURCE_GROUP \
  --workspace-name $LOG_ANALYTICS_WORKSPACE \
  --location $LOCATION

# 워크스페이스 ID 및 키 가져오기
LOG_ANALYTICS_WORKSPACE_ID=$(az monitor log-analytics workspace show \
  --resource-group $RESOURCE_GROUP \
  --workspace-name $LOG_ANALYTICS_WORKSPACE \
  --query customerId \
  --output tsv)

LOG_ANALYTICS_KEY=$(az monitor log-analytics workspace get-shared-keys \
  --resource-group $RESOURCE_GROUP \
  --workspace-name $LOG_ANALYTICS_WORKSPACE \
  --query primarySharedKey \
  --output tsv)
```

### 3.3 Container Apps 환경 생성

```bash
# Container Apps 환경 생성
az containerapp env create \
  --name $ENVIRONMENT_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --logs-workspace-id $LOG_ANALYTICS_WORKSPACE_ID \
  --logs-workspace-key $LOG_ANALYTICS_KEY

# 환경 생성 확인
az containerapp env show \
  --name $ENVIRONMENT_NAME \
  --resource-group $RESOURCE_GROUP \
  --output table
```

**예상 출력:**
```
Location       Name           ProvisioningState    ResourceGroup
-------------  -------------  -------------------  -------------
koreacentral   cae-docuchat   Succeeded           rg-docuchat
```

---

## 4. Azure Database for PostgreSQL 설정

### 4.1 PostgreSQL Flexible Server SKU 비교

| SKU 티어 | vCore | RAM | 저장소 | 가격(월, 예상) | 용도 |
|----------|-------|-----|--------|---------------|------|
| Burstable B1ms | 1 | 2GB | 32GB | ~$15-25 | 개발/테스트 |
| Burstable B2s | 2 | 4GB | 64GB | ~$30-50 | 소규모 프로덕션 |
| General Purpose D2s_v3 | 2 | 8GB | 128GB | ~$100+ | 프로덕션 |

**권장:** 개발/학습 목적으로는 `Burstable B1ms` 사용

### 4.2 PostgreSQL Flexible Server 생성

```bash
# 변수 설정
POSTGRES_SERVER_NAME="psql-docuchat"
POSTGRES_ADMIN_USER="docuchat_admin"
POSTGRES_ADMIN_PASSWORD="<강력한_비밀번호_입력>"  # 최소 8자, 대소문자+숫자+특수문자
POSTGRES_SKU="Standard_B1ms"
POSTGRES_TIER="Burstable"
POSTGRES_VERSION="15"
POSTGRES_STORAGE_SIZE="32"  # GB

# PostgreSQL Flexible Server 생성
az postgres flexible-server create \
  --resource-group $RESOURCE_GROUP \
  --name $POSTGRES_SERVER_NAME \
  --location $LOCATION \
  --admin-user $POSTGRES_ADMIN_USER \
  --admin-password $POSTGRES_ADMIN_PASSWORD \
  --sku-name $POSTGRES_SKU \
  --tier $POSTGRES_TIER \
  --version $POSTGRES_VERSION \
  --storage-size $POSTGRES_STORAGE_SIZE \
  --public-access 0.0.0.0  # Container Apps에서 접근 허용
```

**중요:** 비밀번호는 안전하게 보관하세요!

### 4.3 데이터베이스 생성

```bash
# 데이터베이스 생성
az postgres flexible-server db create \
  --resource-group $RESOURCE_GROUP \
  --server-name $POSTGRES_SERVER_NAME \
  --database-name docuchat_db

# 데이터베이스 목록 확인
az postgres flexible-server db list \
  --resource-group $RESOURCE_GROUP \
  --server-name $POSTGRES_SERVER_NAME \
  --output table
```

### 4.4 방화벽 규칙 설정

```bash
# Azure 서비스 접근 허용 (Container Apps에서 접근)
az postgres flexible-server firewall-rule create \
  --resource-group $RESOURCE_GROUP \
  --name $POSTGRES_SERVER_NAME \
  --rule-name AllowAzureServices \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0

# (선택) 로컬 개발 IP 허용
# MY_IP=$(curl -s ifconfig.me)
# az postgres flexible-server firewall-rule create \
#   --resource-group $RESOURCE_GROUP \
#   --name $POSTGRES_SERVER_NAME \
#   --rule-name AllowMyIP \
#   --start-ip-address $MY_IP \
#   --end-ip-address $MY_IP
```

### 4.5 연결 문자열 확인

```bash
# 서버 FQDN 확인
POSTGRES_HOST=$(az postgres flexible-server show \
  --resource-group $RESOURCE_GROUP \
  --name $POSTGRES_SERVER_NAME \
  --query fullyQualifiedDomainName \
  --output tsv)

echo "PostgreSQL Host: $POSTGRES_HOST"
# 출력 예: psql-docuchat.postgres.database.azure.com

# 연결 문자열 형식
echo "DATABASE_URL=postgresql://${POSTGRES_ADMIN_USER}:${POSTGRES_ADMIN_PASSWORD}@${POSTGRES_HOST}:5432/docuchat_db?sslmode=require"
```

---

## 5. 백엔드 Container App 배포

### 5.1 ACR 자격 증명 가져오기

```bash
# ACR 로그인 서버
ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --query loginServer --output tsv)

# ACR 자격 증명
ACR_USERNAME=$(az acr credential show --name $ACR_NAME --query username --output tsv)
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query "passwords[0].value" --output tsv)
```

### 5.2 백엔드 앱 생성

```bash
# 변수 설정
BACKEND_APP_NAME="ca-docuchat-backend"
BACKEND_IMAGE="docuchat.azurecr.io/docuchat-backend:v1.0.0"

# 백엔드 Container App 생성
az containerapp create \
  --name $BACKEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --environment $ENVIRONMENT_NAME \
  --image $BACKEND_IMAGE \
  --registry-server $ACR_LOGIN_SERVER \
  --registry-username $ACR_USERNAME \
  --registry-password $ACR_PASSWORD \
  --target-port 8000 \
  --ingress external \
  --cpu 0.5 \
  --memory 1Gi \
  --min-replicas 0 \
  --max-replicas 3 \
  --env-vars \
    "APP_ENV=production" \
    "DATABASE_URL=secretref:database-url" \
    "GOOGLE_API_KEY=secretref:google-api-key"
```

### 5.3 시크릿 설정

```bash
# 시크릿 추가
az containerapp secret set \
  --name $BACKEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --secrets \
    "database-url=postgresql://${POSTGRES_ADMIN_USER}:${POSTGRES_ADMIN_PASSWORD}@${POSTGRES_HOST}:5432/docuchat_db?sslmode=require" \
    "google-api-key=<YOUR_GOOGLE_API_KEY>"
```

### 5.4 백엔드 URL 확인

```bash
# 백엔드 앱 URL 확인
BACKEND_URL=$(az containerapp show \
  --name $BACKEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query properties.configuration.ingress.fqdn \
  --output tsv)

echo "Backend URL: https://$BACKEND_URL"
```

---

## 6. 프론트엔드 Container App 배포

### 6.1 프론트엔드 앱 생성

```bash
# 변수 설정
FRONTEND_APP_NAME="ca-docuchat-frontend"
FRONTEND_IMAGE="docuchat.azurecr.io/docuchat-frontend:v1.0.0"

# 프론트엔드 Container App 생성
az containerapp create \
  --name $FRONTEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --environment $ENVIRONMENT_NAME \
  --image $FRONTEND_IMAGE \
  --registry-server $ACR_LOGIN_SERVER \
  --registry-username $ACR_USERNAME \
  --registry-password $ACR_PASSWORD \
  --target-port 3000 \
  --ingress external \
  --cpu 0.5 \
  --memory 1Gi \
  --min-replicas 0 \
  --max-replicas 3 \
  --env-vars \
    "NEXT_PUBLIC_API_URL=https://$BACKEND_URL"
```

### 6.2 프론트엔드 URL 확인

```bash
# 프론트엔드 앱 URL 확인
FRONTEND_URL=$(az containerapp show \
  --name $FRONTEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query properties.configuration.ingress.fqdn \
  --output tsv)

echo "Frontend URL: https://$FRONTEND_URL"
```

---

## 7. 환경 변수 및 시크릿 설정

### 7.1 환경 변수 구성

**백엔드 환경 변수:**

| 변수명 | 설명 | 예시 값 |
|--------|------|---------|
| `APP_ENV` | 애플리케이션 환경 | `production` |
| `DATABASE_URL` | PostgreSQL 연결 문자열 | (시크릿 참조) |
| `GOOGLE_API_KEY` | Google Gemini API 키 | (시크릿 참조) |

**프론트엔드 환경 변수:**

| 변수명 | 설명 | 예시 값 |
|--------|------|---------|
| `NEXT_PUBLIC_API_URL` | 백엔드 API URL | `https://ca-docuchat-backend.xxx.azurecontainerapps.io` |

### 7.2 환경 변수 업데이트

```bash
# 백엔드 환경 변수 업데이트
az containerapp update \
  --name $BACKEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --set-env-vars \
    "NEW_VAR=value" \
    "ANOTHER_VAR=secretref:some-secret"

# 프론트엔드 환경 변수 업데이트
az containerapp update \
  --name $FRONTEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --set-env-vars \
    "NEXT_PUBLIC_API_URL=https://$BACKEND_URL"
```

### 7.3 시크릿 관리

```bash
# 시크릿 목록 확인
az containerapp secret list \
  --name $BACKEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --output table

# 시크릿 추가/업데이트
az containerapp secret set \
  --name $BACKEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --secrets "new-secret=secret-value"

# 시크릿 삭제
az containerapp secret remove \
  --name $BACKEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --secret-names "old-secret"
```

---

## 8. Ingress 및 외부 접근 설정

### 8.1 Ingress 설정 옵션

| 옵션 | 설명 | 사용 사례 |
|------|------|----------|
| `external` | 인터넷에서 접근 가능 | 프론트엔드, 공개 API |
| `internal` | Container Apps 환경 내에서만 접근 | 내부 서비스, 마이크로서비스 |
| 비활성화 | Ingress 없음 | 백그라운드 작업자 |

### 8.2 Ingress 구성 변경

```bash
# 외부 Ingress 활성화 (프론트엔드)
az containerapp ingress enable \
  --name $FRONTEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --type external \
  --target-port 3000 \
  --transport http

# 내부 Ingress로 변경 (선택적 - 백엔드를 내부로)
# az containerapp ingress enable \
#   --name $BACKEND_APP_NAME \
#   --resource-group $RESOURCE_GROUP \
#   --type internal \
#   --target-port 8000
```

### 8.3 CORS 설정 (백엔드)

백엔드 애플리케이션 코드에서 CORS를 설정하세요:

```python
# src/main.py (FastAPI)
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://ca-docuchat-frontend.xxx.azurecontainerapps.io",
        # 개발 환경
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 8.4 커스텀 도메인 설정 (선택)

```bash
# 커스텀 도메인 추가
az containerapp hostname add \
  --name $FRONTEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --hostname "app.docuchat.com"

# 관리형 인증서 바인딩
az containerapp hostname bind \
  --name $FRONTEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --hostname "app.docuchat.com" \
  --environment $ENVIRONMENT_NAME \
  --validation-method CNAME
```

---

## 9. Health Probes 설정

Health Probes는 컨테이너의 상태를 모니터링합니다.

### 9.1 Probe 유형

| Probe 유형 | 목적 | 실패 시 동작 |
|-----------|------|-------------|
| Startup | 컨테이너 시작 확인 | 시작 실패로 판단 |
| Liveness | 컨테이너 정상 동작 확인 | 컨테이너 재시작 |
| Readiness | 트래픽 수신 가능 여부 | 트래픽 라우팅 중지 |

### 9.2 백엔드 Health Endpoint 구현

백엔드 코드에 health check 엔드포인트 추가:

```python
# src/api/v1/health.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.core.database import get_db

router = APIRouter()

@router.get("/health")
async def health_check():
    return {"status": "healthy"}

@router.get("/health/ready")
async def readiness_check(db: Session = Depends(get_db)):
    # 데이터베이스 연결 확인
    try:
        db.execute("SELECT 1")
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        return {"status": "not ready", "database": str(e)}
```

### 9.3 YAML을 통한 Probe 설정

Container App YAML 템플릿:

```yaml
# containerapp.yaml
properties:
  template:
    containers:
      - name: backend
        image: docuchat.azurecr.io/docuchat-backend:v1.0.0
        probes:
          - type: Startup
            httpGet:
              path: /api/v1/health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 10
            failureThreshold: 30
          - type: Liveness
            httpGet:
              path: /api/v1/health
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 30
            failureThreshold: 3
          - type: Readiness
            httpGet:
              path: /api/v1/health/ready
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 10
            failureThreshold: 3
```

### 9.4 CLI로 Probe 설정

```bash
# YAML 파일로 앱 업데이트
az containerapp update \
  --name $BACKEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --yaml containerapp.yaml
```

---

## 10. 스케일링 설정

### 10.1 스케일링 규칙 유형

| 규칙 유형 | 트리거 | 사용 사례 |
|----------|--------|----------|
| HTTP | 동시 요청 수 | 웹 애플리케이션 |
| CPU | CPU 사용률 | 컴퓨팅 집약적 작업 |
| Memory | 메모리 사용률 | 메모리 집약적 작업 |
| Custom | KEDA 스케일러 | 큐, 이벤트 기반 |

### 10.2 HTTP 기반 스케일링 (기본)

```bash
# 스케일링 설정 업데이트
az containerapp update \
  --name $BACKEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --min-replicas 0 \
  --max-replicas 5 \
  --scale-rule-name "http-rule" \
  --scale-rule-type "http" \
  --scale-rule-http-concurrency 50
```

### 10.3 스케일링 설정 확인

```bash
# 현재 스케일링 설정 확인
az containerapp show \
  --name $BACKEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query properties.template.scale

# 현재 replica 수 확인
az containerapp replica list \
  --name $BACKEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --output table
```

### 10.4 0으로 스케일 다운 (Scale to Zero)

개발/테스트 환경에서 비용 절감을 위해:

```bash
# 최소 replica를 0으로 설정
az containerapp update \
  --name $BACKEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --min-replicas 0

# 프로덕션에서는 최소 1 유지 권장
az containerapp update \
  --name $BACKEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --min-replicas 1
```

---

## 11. Azure Portal 사용 방법

### 11.1 Container Apps 환경 생성

1. [Azure Portal](https://portal.azure.com) 로그인
2. 상단 검색창에 "Container Apps" 입력
3. "Container Apps" → "+ 만들기"
4. **기본 사항:**
   - 구독: 본인 구독 선택
   - 리소스 그룹: `rg-docuchat`
   - Container App 이름: `ca-docuchat-backend`
   - 지역: `Korea Central`
   - Container Apps 환경: "새로 만들기" → `cae-docuchat`
5. **컨테이너:**
   - 이미지 원본: Azure Container Registry
   - 레지스트리: `docuchat.azurecr.io`
   - 이미지: `docuchat-backend`
   - 태그: `v1.0.0`
6. **Ingress:**
   - Ingress: 사용
   - 수신 트래픽: 어디서나 트래픽 허용
   - 대상 포트: `8000`
7. "검토 + 만들기" → "만들기"

### 11.2 환경 변수 설정 (Portal)

1. 생성된 Container App 클릭
2. 왼쪽 메뉴 → "컨테이너" → "환경 변수"
3. "+ 추가"로 환경 변수 추가
4. 시크릿 참조: "시크릿" 탭에서 먼저 시크릿 생성 후 참조

### 11.3 스케일링 설정 (Portal)

1. Container App → "크기 조정"
2. 최소/최대 복제본 설정
3. 규칙 추가 (HTTP, CPU 등)

### 11.4 로그 확인 (Portal)

1. Container App → "로그"
2. KQL 쿼리 실행:

```kql
// 최근 로그 조회
ContainerAppConsoleLogs_CL
| where ContainerAppName_s == "ca-docuchat-backend"
| order by TimeGenerated desc
| take 100
```

---

## 12. 비용 추정

### 12.1 Container Apps 가격 (2025년 기준)

| 리소스 | 단위 | 가격 (예상) |
|--------|------|------------|
| vCPU | 초당 | ~$0.000024 |
| 메모리 | GiB-초당 | ~$0.000003 |
| 요청 | 백만 건당 | ~$0.40 |

### 12.2 월간 비용 추정 (개발 환경)

**가정:**
- 백엔드: 0.5 vCPU, 1GB RAM, 하루 8시간 운영
- 프론트엔드: 0.5 vCPU, 1GB RAM, 하루 8시간 운영
- Scale to Zero 사용

| 항목 | 예상 비용 (월) |
|------|--------------|
| Container Apps (2개) | ~$15-30 |
| PostgreSQL B1ms | ~$15-25 |
| ACR Basic | ~$5 |
| Log Analytics | ~$5 |
| **총계** | **~$40-65** |

### 12.3 비용 절감 팁

1. **Scale to Zero**: 트래픽 없을 때 자동 중지
2. **개발 시간에만 운영**: 업무 시간 외 중지 스크립트 사용
3. **적절한 SKU 선택**: 필요 이상의 리소스 할당 지양
4. **로그 보존 기간 단축**: 기본 30일 → 7일

```bash
# 리소스 중지 스크립트 (비용 절감)
az containerapp update --name $BACKEND_APP_NAME --resource-group $RESOURCE_GROUP --min-replicas 0 --max-replicas 0
az containerapp update --name $FRONTEND_APP_NAME --resource-group $RESOURCE_GROUP --min-replicas 0 --max-replicas 0

# 리소스 시작 스크립트
az containerapp update --name $BACKEND_APP_NAME --resource-group $RESOURCE_GROUP --min-replicas 0 --max-replicas 3
az containerapp update --name $FRONTEND_APP_NAME --resource-group $RESOURCE_GROUP --min-replicas 0 --max-replicas 3
```

---

## 13. 트러블슈팅

### 13.1 자주 발생하는 문제

#### 1. 컨테이너 시작 실패

```
Error: Container failed to start
```

**진단:**
```bash
# 로그 확인
az containerapp logs show \
  --name $BACKEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --type console \
  --tail 100
```

**해결:**
- 이미지 태그 확인
- 환경 변수 확인 (DATABASE_URL 등)
- 포트 설정 확인

#### 2. 데이터베이스 연결 실패

```
Error: Connection refused to database
```

**진단:**
```bash
# PostgreSQL 방화벽 규칙 확인
az postgres flexible-server firewall-rule list \
  --resource-group $RESOURCE_GROUP \
  --name $POSTGRES_SERVER_NAME \
  --output table
```

**해결:**
```bash
# Azure 서비스 접근 허용 규칙 추가
az postgres flexible-server firewall-rule create \
  --resource-group $RESOURCE_GROUP \
  --name $POSTGRES_SERVER_NAME \
  --rule-name AllowAzureServices \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0
```

#### 3. ACR 이미지 풀 실패

```
Error: ImagePullBackOff
```

**해결:**
```bash
# ACR 자격 증명 업데이트
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query "passwords[0].value" --output tsv)

az containerapp registry set \
  --name $BACKEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --server $ACR_LOGIN_SERVER \
  --username $ACR_USERNAME \
  --password $ACR_PASSWORD
```

#### 4. 환경 변수 누락

**진단:**
```bash
# 환경 변수 확인
az containerapp show \
  --name $BACKEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query properties.template.containers[0].env
```

### 13.2 유용한 진단 명령어

```bash
# 앱 상태 확인
az containerapp show \
  --name $BACKEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query properties.provisioningState

# 현재 replica 상태
az containerapp replica list \
  --name $BACKEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --output table

# 최근 이벤트 로그
az containerapp logs show \
  --name $BACKEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --type system

# 앱 재시작
az containerapp revision restart \
  --name $BACKEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --revision <revision-name>

# 새 revision 배포
az containerapp update \
  --name $BACKEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --image docuchat.azurecr.io/docuchat-backend:v1.0.1
```

### 13.3 로그 분석 쿼리 (KQL)

Log Analytics에서 사용:

```kql
// 오류 로그만 조회
ContainerAppConsoleLogs_CL
| where ContainerAppName_s == "ca-docuchat-backend"
| where Log_s contains "error" or Log_s contains "Error" or Log_s contains "ERROR"
| order by TimeGenerated desc
| take 50

// 시간대별 요청 수
ContainerAppConsoleLogs_CL
| where ContainerAppName_s == "ca-docuchat-backend"
| summarize RequestCount = count() by bin(TimeGenerated, 1h)
| render timechart

// 컨테이너 재시작 이벤트
ContainerAppSystemLogs_CL
| where ContainerAppName_s == "ca-docuchat-backend"
| where Reason_s == "Pulled" or Reason_s == "Started"
| order by TimeGenerated desc
```

---

## 다음 단계

이 가이드를 완료하면:

1. ✅ Container Apps 환경 생성 완료
2. ✅ PostgreSQL Flexible Server 설정 완료
3. ✅ 백엔드/프론트엔드 앱 배포 완료
4. ✅ Ingress 및 스케일링 구성 완료

다음 단계:
- [GitHub Actions CI/CD 구성](./github-actions-cicd.md) (CHA-70)
- [모니터링 및 알림 설정](./monitoring-setup.md) (향후)

---

## 참고 자료

- [Azure Container Apps 공식 문서](https://learn.microsoft.com/azure/container-apps/)
- [Azure Database for PostgreSQL 문서](https://learn.microsoft.com/azure/postgresql/)
- [Container Apps 가격 책정](https://azure.microsoft.com/pricing/details/container-apps/)
- [Container Apps 샘플](https://github.com/Azure-Samples/container-apps-samples)
- [KEDA 스케일러 목록](https://keda.sh/docs/latest/scalers/)

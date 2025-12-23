# Azure Container Registry (ACR) 설정 가이드

## 목차

1. [사전 요구사항](#1-사전-요구사항)
2. [리소스 그룹 생성](#2-리소스-그룹-생성)
3. [Azure Container Registry 생성](#3-azure-container-registry-생성)
4. [로그인 및 인증](#4-로그인-및-인증)
5. [이미지 빌드 및 푸시](#5-이미지-빌드-및-푸시)
6. [GitHub Actions용 서비스 주체 설정](#6-github-actions용-서비스-주체-설정)
7. [Azure Portal 사용 방법](#7-azure-portal-사용-방법)
8. [트러블슈팅](#8-트러블슈팅)

---

## 1. 사전 요구사항

### 필수 항목

| 항목 | 설명 | 확인 방법 |
|------|------|----------|
| Azure 구독 | 활성 Azure 구독 필요 | Azure Portal 로그인 후 확인 |
| Azure CLI | v2.50.0 이상 권장 | `az --version` |
| Docker | 로컬 이미지 빌드용 | `docker --version` |

### Azure CLI 설치

**Windows (PowerShell):**
```powershell
# winget으로 설치
winget install -e --id Microsoft.AzureCLI

# 또는 MSI 설치 프로그램 다운로드
# https://aka.ms/installazurecliwindows
```

**macOS:**
```bash
brew update && brew install azure-cli
```

**Linux (Ubuntu/Debian):**
```bash
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

### Azure CLI 로그인

```bash
# 브라우저 기반 로그인 (권장)
az login

# 디바이스 코드 로그인 (브라우저 없는 환경)
az login --use-device-code

# 로그인 확인
az account show
```

---

## 2. 리소스 그룹 생성

리소스 그룹은 Azure 리소스를 논리적으로 그룹화하는 컨테이너입니다.

### Azure CLI

```bash
# 변수 설정
RESOURCE_GROUP="rg-docuchat"
LOCATION="koreacentral"

# 리소스 그룹 생성
az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION

# 생성 확인
az group show --name $RESOURCE_GROUP --output table
```

**예상 출력:**
```
Location       Name
-------------  -----------
koreacentral   rg-docuchat
```

### 사용 가능한 위치 목록

```bash
# 한국 리전 확인
az account list-locations --query "[?contains(name, 'korea')]" --output table
```

| 위치 이름 | 표시 이름 |
|-----------|----------|
| koreacentral | Korea Central (서울) |
| koreasouth | Korea South (부산) |

---

## 3. Azure Container Registry 생성

### ACR SKU 비교

| SKU | 저장소 | 분당 읽기 작업 | 가격(월) | 용도 |
|-----|--------|---------------|---------|------|
| Basic | 10GB | 1,000 | ~$5 | 개발/테스트 |
| Standard | 100GB | 10,000 | ~$20 | 소규모 프로덕션 |
| Premium | 500GB | 10,000+ | ~$50 | 대규모 프로덕션, 지역 복제 |

**권장:** 학습/개발 목적으로는 `Basic` SKU 사용

### Azure CLI

```bash
# 변수 설정
ACR_NAME="docuchat"
RESOURCE_GROUP="rg-docuchat"
SKU="Basic"

# ACR 이름 가용성 확인 (전역 고유해야 함)
az acr check-name --name $ACR_NAME

# ACR 생성
az acr create \
  --resource-group $RESOURCE_GROUP \
  --name $ACR_NAME \
  --sku $SKU \
  --admin-enabled true

# 생성 확인
az acr show --name $ACR_NAME --output table
```

**예상 출력:**
```
NAME       RESOURCE GROUP   LOCATION       SKU    LOGIN SERVER           CREATION DATE
---------  ---------------  -------------  -----  ---------------------  -------------------------
docuchat   rg-docuchat      koreacentral   Basic  docuchat.azurecr.io    2025-12-21T00:00:00+00:00
```

### 중요 정보 확인

```bash
# 로그인 서버 URL 확인
az acr show --name $ACR_NAME --query loginServer --output tsv
# 출력: docuchat.azurecr.io

# 관리자 자격 증명 확인 (개발 환경용)
az acr credential show --name $ACR_NAME
```

---

## 4. 로그인 및 인증

### 방법 1: Azure CLI 통합 로그인 (권장)

```bash
# ACR에 로그인 (Azure 자격 증명 사용)
az acr login --name docuchat

# 성공 메시지
# Login Succeeded
```

### 방법 2: Docker 직접 로그인

```bash
# 관리자 자격 증명 가져오기
ACR_NAME="docuchat"
USERNAME=$(az acr credential show --name $ACR_NAME --query username --output tsv)
PASSWORD=$(az acr credential show --name $ACR_NAME --query "passwords[0].value" --output tsv)

# Docker 로그인
docker login docuchat.azurecr.io --username $USERNAME --password $PASSWORD
```

### 로그인 확인

```bash
# Docker 설정 파일에서 확인
cat ~/.docker/config.json | grep docuchat
```

---

## 5. 이미지 빌드 및 푸시

### 로컬에서 빌드 후 푸시

```bash
# 변수 설정
ACR_NAME="docuchat"
ACR_LOGIN_SERVER="docuchat.azurecr.io"
IMAGE_TAG="v1.0.0"

# 백엔드 이미지 빌드
docker build -t $ACR_LOGIN_SERVER/docuchat-backend:$IMAGE_TAG -f Dockerfile .

# 프론트엔드 이미지 빌드
docker build -t $ACR_LOGIN_SERVER/docuchat-frontend:$IMAGE_TAG -f frontend/Dockerfile ./frontend

# ACR에 푸시
docker push $ACR_LOGIN_SERVER/docuchat-backend:$IMAGE_TAG
docker push $ACR_LOGIN_SERVER/docuchat-frontend:$IMAGE_TAG
```

### ACR Tasks로 원격 빌드 (권장)

로컬에 Docker가 없어도 ACR에서 직접 빌드할 수 있습니다.

```bash
# 백엔드 이미지를 ACR에서 직접 빌드
az acr build \
  --registry $ACR_NAME \
  --image docuchat-backend:$IMAGE_TAG \
  --file Dockerfile \
  .

# 프론트엔드 이미지를 ACR에서 직접 빌드
az acr build \
  --registry $ACR_NAME \
  --image docuchat-frontend:$IMAGE_TAG \
  --file frontend/Dockerfile \
  ./frontend
```

### 이미지 목록 확인

```bash
# 레포지토리 목록
az acr repository list --name $ACR_NAME --output table

# 특정 이미지의 태그 목록
az acr repository show-tags --name $ACR_NAME --repository docuchat-backend --output table
```

---

## 6. GitHub Actions용 서비스 주체 설정

CI/CD 파이프라인에서 ACR에 접근하려면 서비스 주체(Service Principal)가 필요합니다.

### 서비스 주체 생성

```bash
# 변수 설정
ACR_NAME="docuchat"
SERVICE_PRINCIPAL_NAME="sp-docuchat-github"

# ACR 리소스 ID 가져오기
ACR_REGISTRY_ID=$(az acr show --name $ACR_NAME --query "id" --output tsv)

# 서비스 주체 생성 (acrpush 역할 부여)
az ad sp create-for-rbac \
  --name $SERVICE_PRINCIPAL_NAME \
  --scopes $ACR_REGISTRY_ID \
  --role acrpush \
  --sdk-auth
```

**출력 예시 (GitHub Secrets에 저장할 값):**
```json
{
  "clientId": "<CLIENT_ID>",
  "clientSecret": "<CLIENT_SECRET>",
  "subscriptionId": "<SUBSCRIPTION_ID>",
  "tenantId": "<TENANT_ID>",
  "activeDirectoryEndpointUrl": "https://login.microsoftonline.com",
  "resourceManagerEndpointUrl": "https://management.azure.com/",
  "activeDirectoryGraphResourceId": "https://graph.windows.net/",
  "sqlManagementEndpointUrl": "https://management.core.windows.net:8443/",
  "galleryEndpointUrl": "https://gallery.azure.com/",
  "managementEndpointUrl": "https://management.core.windows.net/"
}
```

### GitHub Secrets 설정

GitHub Repository → Settings → Secrets and variables → Actions에서 다음 시크릿 추가:

| Secret Name | Value |
|-------------|-------|
| `AZURE_CREDENTIALS` | 위 JSON 전체 출력 |
| `ACR_LOGIN_SERVER` | `docuchat.azurecr.io` |
| `ACR_USERNAME` | `<clientId>` |
| `ACR_PASSWORD` | `<clientSecret>` |

### GitHub Actions 워크플로우 예시

```yaml
# .github/workflows/docker-build.yml
name: Build and Push to ACR

on:
  push:
    branches: [main]

env:
  ACR_LOGIN_SERVER: ${{ secrets.ACR_LOGIN_SERVER }}

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Login to Azure
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Login to ACR
        uses: azure/docker-login@v1
        with:
          login-server: ${{ secrets.ACR_LOGIN_SERVER }}
          username: ${{ secrets.ACR_USERNAME }}
          password: ${{ secrets.ACR_PASSWORD }}

      - name: Build and push backend image
        run: |
          docker build -t $ACR_LOGIN_SERVER/docuchat-backend:${{ github.sha }} .
          docker push $ACR_LOGIN_SERVER/docuchat-backend:${{ github.sha }}

      - name: Build and push frontend image
        run: |
          docker build -t $ACR_LOGIN_SERVER/docuchat-frontend:${{ github.sha }} -f frontend/Dockerfile ./frontend
          docker push $ACR_LOGIN_SERVER/docuchat-frontend:${{ github.sha }}
```

---

## 7. Azure Portal 사용 방법

Azure CLI 대신 Azure Portal을 사용하는 경우:

### 7.1 리소스 그룹 생성

1. [Azure Portal](https://portal.azure.com) 로그인
2. 상단 검색창에 "리소스 그룹" 입력
3. "리소스 그룹" 클릭 → "+ 만들기"
4. 설정:
   - 구독: 본인 구독 선택
   - 리소스 그룹: `rg-docuchat`
   - 지역: `Korea Central`
5. "검토 + 만들기" → "만들기"

### 7.2 Container Registry 생성

1. 상단 검색창에 "Container Registry" 입력
2. "Container Registries" 클릭 → "+ 만들기"
3. 기본 사항:
   - 구독: 본인 구독 선택
   - 리소스 그룹: `rg-docuchat`
   - 레지스트리 이름: `docuchat` (전역 고유)
   - 위치: `Korea Central`
   - SKU: `Basic`
4. "검토 + 만들기" → "만들기"

### 7.3 관리자 계정 활성화

1. 생성된 Container Registry 클릭
2. 왼쪽 메뉴 → "액세스 키"
3. "관리 사용자" 토글 활성화
4. 사용자 이름과 비밀번호 확인 (Docker 로그인용)

---

## 8. 트러블슈팅

### 자주 발생하는 문제

#### 1. ACR 이름 사용 불가

```
Error: The registry name is already in use
```

**해결:**
```bash
# 다른 이름 시도
az acr check-name --name docuchat2024
```

#### 2. Docker 로그인 실패

```
Error: unauthorized: authentication required
```

**해결:**
```bash
# ACR 로그인 재시도
az acr login --name docuchat

# 또는 관리자 자격 증명 확인
az acr credential show --name docuchat
```

#### 3. 이미지 푸시 권한 없음

```
Error: denied: requested access to the resource is denied
```

**해결:**
```bash
# 역할 확인
az role assignment list --scope /subscriptions/<SUB_ID>/resourceGroups/rg-docuchat/providers/Microsoft.ContainerRegistry/registries/docuchat

# acrpush 역할 추가
az role assignment create \
  --assignee <USER_OR_SP_ID> \
  --scope <ACR_RESOURCE_ID> \
  --role acrpush
```

#### 4. ACR 빌드 타임아웃

```
Error: Build timed out
```

**해결:**
```bash
# 타임아웃 시간 증가 (초 단위)
az acr build \
  --registry $ACR_NAME \
  --image docuchat-backend:latest \
  --timeout 3600 \
  .
```

### 유용한 진단 명령어

```bash
# ACR 상태 확인
az acr show --name docuchat --query provisioningState

# ACR 사용량 확인
az acr show-usage --name docuchat --output table

# ACR 로그 확인
az acr task logs --name docuchat

# 이미지 삭제 (저장소 정리)
az acr repository delete --name docuchat --repository docuchat-backend --yes
```

---

## 다음 단계

이 가이드를 완료하면:

1. ✅ Azure Container Registry 생성 완료
2. ✅ Docker 이미지 빌드 및 푸시 가능
3. ✅ GitHub Actions 연동 준비 완료

다음 단계:
- [Azure Container Apps 설정](./azure-container-apps-setup_kr.md)

---

## 참고 자료

- [Azure Container Registry 공식 문서](https://learn.microsoft.com/azure/container-registry/)
- [Azure CLI 설치 가이드](https://learn.microsoft.com/cli/azure/install-azure-cli)
- [ACR Tasks 개요](https://learn.microsoft.com/azure/container-registry/container-registry-tasks-overview)
- [GitHub Actions에서 ACR 사용](https://learn.microsoft.com/azure/container-registry/container-registry-github-action)

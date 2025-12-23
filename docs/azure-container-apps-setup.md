# Azure Container Apps Deployment Guide

> Prerequisite: [Azure Container Registry Setup](./azure-acr-setup.md)

## Table of Contents

1. [Overview](#1-overview)
2. [Prerequisites](#2-prerequisites)
3. [Create Container Apps Environment](#3-create-container-apps-environment)
4. [Azure Database for PostgreSQL Setup](#4-azure-database-for-postgresql-setup)
5. [Deploy Backend Container App](#5-deploy-backend-container-app)
6. [Deploy Frontend Container App](#6-deploy-frontend-container-app)
7. [Environment Variables and Secrets](#7-environment-variables-and-secrets)
8. [Ingress and External Access](#8-ingress-and-external-access)
9. [Health Probes](#9-health-probes)
10. [Scaling Configuration](#10-scaling-configuration)
11. [Azure Portal Method](#11-azure-portal-method)
12. [Cost Estimation](#12-cost-estimation)
13. [Troubleshooting](#13-troubleshooting)

---

## 1. Overview

### What is Azure Container Apps?

Azure Container Apps is a serverless container platform that runs containerized applications without the complexity of Kubernetes.

### Architecture

```
                    ┌─────────────────────────────────────────────┐
                    │       Azure Container Apps Environment      │
                    │              (cae-docuchat)                 │
                    │                                             │
┌─────────┐        │  ┌─────────────────┐  ┌─────────────────┐  │        ┌─────────────────┐
│  User   │───────▶│  │ Frontend App    │  │ Backend App     │──│──────▶ │ PostgreSQL      │
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

### Resource Naming Convention

| Resource Type | Name | Description |
|---------------|------|-------------|
| Resource Group | `rg-docuchat` | All resources grouped |
| Container Apps Environment | `cae-docuchat` | Container app runtime |
| Backend App | `ca-docuchat-backend` | FastAPI backend |
| Frontend App | `ca-docuchat-frontend` | Next.js frontend |
| PostgreSQL Server | `psql-docuchat` | Database server |
| Log Analytics | `log-docuchat` | Log collection |

---

## 2. Prerequisites

### Required Items

| Item | Description | Verification |
|------|-------------|--------------|
| Azure Subscription | Active Azure subscription | Check Azure Portal |
| Azure CLI | v2.50.0 or higher | `az --version` |
| ACR Setup Complete | ACR configured | `az acr show --name docuchat` |
| Docker Images | Pushed to ACR | `az acr repository list --name docuchat` |

### Install Azure CLI Extensions

```bash
# Install Container Apps extension
az extension add --name containerapp --upgrade

# Verify installation
az extension list --query "[?name=='containerapp']" --output table
```

### Register Resource Providers

```bash
# Register Container Apps provider
az provider register --namespace Microsoft.App

# Register Operational Insights provider
az provider register --namespace Microsoft.OperationalInsights

# Check registration status
az provider show --namespace Microsoft.App --query "registrationState"
az provider show --namespace Microsoft.OperationalInsights --query "registrationState"
```

---

## 3. Create Container Apps Environment

### 3.1 Set Variables

```bash
# Common variables
RESOURCE_GROUP="rg-docuchat"
LOCATION="koreacentral"
ENVIRONMENT_NAME="cae-docuchat"
LOG_ANALYTICS_WORKSPACE="log-docuchat"
ACR_NAME="docuchat"
```

### 3.2 Create Log Analytics Workspace

```bash
# Create Log Analytics workspace
az monitor log-analytics workspace create \
  --resource-group $RESOURCE_GROUP \
  --workspace-name $LOG_ANALYTICS_WORKSPACE \
  --location $LOCATION

# Get workspace ID and key
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

### 3.3 Create Container Apps Environment

```bash
# Create environment
az containerapp env create \
  --name $ENVIRONMENT_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --logs-workspace-id $LOG_ANALYTICS_WORKSPACE_ID \
  --logs-workspace-key $LOG_ANALYTICS_KEY

# Verify creation
az containerapp env show \
  --name $ENVIRONMENT_NAME \
  --resource-group $RESOURCE_GROUP \
  --output table
```

---

## 4. Azure Database for PostgreSQL Setup

### 4.1 SKU Comparison

| SKU Tier | vCore | RAM | Storage | Price/month | Use Case |
|----------|-------|-----|---------|-------------|----------|
| Burstable B1ms | 1 | 2GB | 32GB | ~$15-25 | Dev/Test |
| Burstable B2s | 2 | 4GB | 64GB | ~$30-50 | Small production |
| General Purpose D2s_v3 | 2 | 8GB | 128GB | ~$100+ | Production |

### 4.2 Create PostgreSQL Flexible Server

```bash
# Set variables
POSTGRES_SERVER_NAME="psql-docuchat"
POSTGRES_ADMIN_USER="docuchat_admin"
POSTGRES_ADMIN_PASSWORD="<strong_password>"  # Min 8 chars, upper/lower/number/special
POSTGRES_SKU="Standard_B1ms"
POSTGRES_TIER="Burstable"
POSTGRES_VERSION="15"
POSTGRES_STORAGE_SIZE="32"  # GB

# Create server
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
  --public-access 0.0.0.0
```

### 4.3 Create Database

```bash
# Create database
az postgres flexible-server db create \
  --resource-group $RESOURCE_GROUP \
  --server-name $POSTGRES_SERVER_NAME \
  --database-name docuchat_db
```

### 4.4 Configure Firewall

```bash
# Allow Azure services access
az postgres flexible-server firewall-rule create \
  --resource-group $RESOURCE_GROUP \
  --name $POSTGRES_SERVER_NAME \
  --rule-name AllowAzureServices \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0
```

### 4.5 Get Connection String

```bash
# Get server FQDN
POSTGRES_HOST=$(az postgres flexible-server show \
  --resource-group $RESOURCE_GROUP \
  --name $POSTGRES_SERVER_NAME \
  --query fullyQualifiedDomainName \
  --output tsv)

echo "DATABASE_URL=postgresql://${POSTGRES_ADMIN_USER}:${POSTGRES_ADMIN_PASSWORD}@${POSTGRES_HOST}:5432/docuchat_db?sslmode=require"
```

---

## 5. Deploy Backend Container App

### 5.1 Get ACR Credentials

```bash
ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --query loginServer --output tsv)
ACR_USERNAME=$(az acr credential show --name $ACR_NAME --query username --output tsv)
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query "passwords[0].value" --output tsv)
```

### 5.2 Create Backend App

```bash
BACKEND_APP_NAME="ca-docuchat-backend"
BACKEND_IMAGE="docuchat.azurecr.io/docuchat-backend:v1.0.0"

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

### 5.3 Set Secrets

```bash
az containerapp secret set \
  --name $BACKEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --secrets \
    "database-url=postgresql://${POSTGRES_ADMIN_USER}:${POSTGRES_ADMIN_PASSWORD}@${POSTGRES_HOST}:5432/docuchat_db?sslmode=require" \
    "google-api-key=<YOUR_GOOGLE_API_KEY>"
```

### 5.4 Get Backend URL

```bash
BACKEND_URL=$(az containerapp show \
  --name $BACKEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query properties.configuration.ingress.fqdn \
  --output tsv)

echo "Backend URL: https://$BACKEND_URL"
```

---

## 6. Deploy Frontend Container App

```bash
FRONTEND_APP_NAME="ca-docuchat-frontend"
FRONTEND_IMAGE="docuchat.azurecr.io/docuchat-frontend:v1.0.0"

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

# Get frontend URL
FRONTEND_URL=$(az containerapp show \
  --name $FRONTEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query properties.configuration.ingress.fqdn \
  --output tsv)

echo "Frontend URL: https://$FRONTEND_URL"
```

---

## 7. Environment Variables and Secrets

### Backend Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `APP_ENV` | Application environment | `production` |
| `DATABASE_URL` | PostgreSQL connection | (secret reference) |
| `GOOGLE_API_KEY` | Google Gemini API key | (secret reference) |

### Frontend Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API URL | `https://ca-docuchat-backend.xxx.azurecontainerapps.io` |

### Update Environment Variables

```bash
az containerapp update \
  --name $BACKEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --set-env-vars "NEW_VAR=value"
```

### Manage Secrets

```bash
# List secrets
az containerapp secret list --name $BACKEND_APP_NAME --resource-group $RESOURCE_GROUP

# Add/update secret
az containerapp secret set --name $BACKEND_APP_NAME --resource-group $RESOURCE_GROUP \
  --secrets "new-secret=secret-value"

# Remove secret
az containerapp secret remove --name $BACKEND_APP_NAME --resource-group $RESOURCE_GROUP \
  --secret-names "old-secret"
```

---

## 8. Ingress and External Access

### Ingress Options

| Option | Description | Use Case |
|--------|-------------|----------|
| `external` | Internet accessible | Frontend, public API |
| `internal` | Only within environment | Internal services |
| Disabled | No ingress | Background workers |

### CORS Configuration (Backend)

```python
# src/main.py (FastAPI)
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://ca-docuchat-frontend.xxx.azurecontainerapps.io",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 9. Health Probes

### Probe Types

| Probe Type | Purpose | On Failure |
|------------|---------|------------|
| Startup | Verify container start | Considered failed start |
| Liveness | Verify running health | Container restart |
| Readiness | Verify traffic ready | Stop routing traffic |

### Backend Health Endpoint

```python
# src/api/v1/health.py
@router.get("/health")
async def health_check():
    return {"status": "healthy"}

@router.get("/health/ready")
async def readiness_check(db: Session = Depends(get_db)):
    try:
        db.execute("SELECT 1")
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        return {"status": "not ready", "database": str(e)}
```

---

## 10. Scaling Configuration

### HTTP-based Scaling

```bash
az containerapp update \
  --name $BACKEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --min-replicas 0 \
  --max-replicas 5 \
  --scale-rule-name "http-rule" \
  --scale-rule-type "http" \
  --scale-rule-http-concurrency 50
```

### Scale to Zero (Cost Saving)

```bash
# Set min replicas to 0
az containerapp update \
  --name $BACKEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --min-replicas 0

# For production, keep at least 1
az containerapp update \
  --name $BACKEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --min-replicas 1
```

---

## 11. Azure Portal Method

1. Login to [Azure Portal](https://portal.azure.com)
2. Search "Container Apps"
3. Click "Container Apps" → "+ Create"
4. **Basics:**
   - Resource group: `rg-docuchat`
   - Container App name: `ca-docuchat-backend`
   - Region: `Korea Central`
5. **Container:**
   - Image source: Azure Container Registry
   - Registry: `docuchat.azurecr.io`
   - Image: `docuchat-backend`
6. **Ingress:**
   - Enable ingress
   - Accept traffic from anywhere
   - Target port: `8000`
7. "Review + create" → "Create"

---

## 12. Cost Estimation

### Monthly Cost Estimate (Development)

| Item | Estimated Cost |
|------|---------------|
| Container Apps (2) | ~$15-30 |
| PostgreSQL B1ms | ~$15-25 |
| ACR Basic | ~$5 |
| Log Analytics | ~$5 |
| **Total** | **~$40-65** |

### Cost Saving Tips

1. **Scale to Zero**: Auto-stop when no traffic
2. **Dev hours only**: Stop outside business hours
3. **Right-size SKU**: Don't over-allocate resources

---

## 13. Troubleshooting

### Common Issues

#### Container Start Failed

```bash
# Check logs
az containerapp logs show \
  --name $BACKEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --type console \
  --tail 100
```

#### Database Connection Failed

```bash
# Check firewall rules
az postgres flexible-server firewall-rule list \
  --resource-group $RESOURCE_GROUP \
  --name $POSTGRES_SERVER_NAME
```

#### ACR Image Pull Failed

```bash
# Update ACR credentials
az containerapp registry set \
  --name $BACKEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --server $ACR_LOGIN_SERVER \
  --username $ACR_USERNAME \
  --password $ACR_PASSWORD
```

### Useful Commands

```bash
# Check app status
az containerapp show --name $BACKEND_APP_NAME --resource-group $RESOURCE_GROUP \
  --query properties.provisioningState

# List replicas
az containerapp replica list --name $BACKEND_APP_NAME --resource-group $RESOURCE_GROUP

# View system logs
az containerapp logs show --name $BACKEND_APP_NAME --resource-group $RESOURCE_GROUP --type system

# Restart app
az containerapp revision restart --name $BACKEND_APP_NAME --resource-group $RESOURCE_GROUP \
  --revision <revision-name>
```

---

## References

- [Azure Container Apps Docs](https://learn.microsoft.com/azure/container-apps/)
- [Azure Database for PostgreSQL](https://learn.microsoft.com/azure/postgresql/)
- [Container Apps Pricing](https://azure.microsoft.com/pricing/details/container-apps/)

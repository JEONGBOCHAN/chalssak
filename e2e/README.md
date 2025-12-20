# E2E Tests

End-to-end API tests using Playwright.

## Setup

```bash
cd e2e
npm install
npx playwright install
```

## Running Tests

### Prerequisites

Make sure the API server is running:

```bash
# From project root
uvicorn src.main:app --reload
```

### Run all tests

```bash
npm test
```

### Run with UI (headed mode)

```bash
npm run test:headed
```

### Run in debug mode

```bash
npm run test:debug
```

### View test report

```bash
npm run test:report
```

## Test Structure

```
e2e/
├── tests/
│   ├── helpers/
│   │   └── api.ts         # API helper functions
│   ├── channel.spec.ts    # Channel CRUD tests
│   ├── document.spec.ts   # Document management tests
│   ├── chat.spec.ts       # Chat/Summarize tests
│   └── user-flow.spec.ts  # Complete user journey tests
├── playwright.config.ts   # Playwright configuration
├── package.json
└── tsconfig.json
```

## Test Scenarios

### Channel Tests
- Create channel
- List channels
- Get channel by ID
- Update channel
- Delete channel
- Validation (empty name, non-existent)

### Document Tests
- List documents
- Upload validation
- URL upload validation
- Delete validation

### Chat Tests
- Send chat message
- Streaming chat
- Channel summarization
- Summary type validation

### User Flow Tests
- Complete journey: Create → Upload → Chat → Delete
- Multiple channel management
- Error handling scenarios
- Admin API operations

## Environment Variables

- `API_BASE_URL`: Base URL for the API (default: `http://localhost:8000`)

## CI/CD

E2E tests run automatically on:
- Push to main/master
- Pull requests to main/master
- Manual trigger via GitHub Actions

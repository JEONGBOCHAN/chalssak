# API 명세

## Base URL

```
http://localhost:8000/api/v1
```

## 인증

현재 버전에서는 인증 없음 (추후 구현)

---

## 채널 API

### 채널 생성

```
POST /channels
```

**Request Body:**
```json
{
  "name": "프로젝트 문서",
  "description": "결제 시스템 관련 문서 모음"
}
```

**Response (201 Created):**
```json
{
  "id": "ch_abc123",
  "name": "프로젝트 문서",
  "description": "결제 시스템 관련 문서 모음",
  "store_name": "fileSearchStores/project-docs-abc123",
  "document_count": 0,
  "created_at": "2025-12-20T12:00:00Z"
}
```

### 채널 목록 조회

```
GET /channels
```

**Query Parameters:**
| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| limit | int | 20 | 최대 조회 개수 |
| offset | int | 0 | 시작 위치 |

**Response (200 OK):**
```json
{
  "channels": [
    {
      "id": "ch_abc123",
      "name": "프로젝트 문서",
      "document_count": 5,
      "created_at": "2025-12-20T12:00:00Z"
    }
  ],
  "total": 1
}
```

### 채널 상세 조회

```
GET /channels/{channel_id}
```

**Response (200 OK):**
```json
{
  "id": "ch_abc123",
  "name": "프로젝트 문서",
  "description": "결제 시스템 관련 문서 모음",
  "store_name": "fileSearchStores/project-docs-abc123",
  "document_count": 5,
  "size_bytes": 15728640,
  "created_at": "2025-12-20T12:00:00Z",
  "updated_at": "2025-12-20T14:00:00Z"
}
```

### 채널 삭제

```
DELETE /channels/{channel_id}
```

**Response (204 No Content)**

---

## 문서 API

### 문서 업로드

```
POST /channels/{channel_id}/documents
```

**Request:** `multipart/form-data`
| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| file | file | O | 업로드할 파일 |
| metadata | json | X | 추가 메타데이터 |

**Response (201 Created):**
```json
{
  "id": "doc_xyz789",
  "channel_id": "ch_abc123",
  "filename": "api-spec.pdf",
  "size_bytes": 1048576,
  "mime_type": "application/pdf",
  "status": "processing",
  "created_at": "2025-12-20T12:00:00Z"
}
```

### 문서 목록 조회

```
GET /channels/{channel_id}/documents
```

**Response (200 OK):**
```json
{
  "documents": [
    {
      "id": "doc_xyz789",
      "filename": "api-spec.pdf",
      "size_bytes": 1048576,
      "status": "ready",
      "created_at": "2025-12-20T12:00:00Z"
    }
  ],
  "total": 1
}
```

### 문서 삭제

```
DELETE /channels/{channel_id}/documents/{document_id}
```

**Response (204 No Content)**

---

## 채팅 API

### 질문하기

```
POST /channels/{channel_id}/chat
```

**Request Body:**
```json
{
  "message": "결제 취소 API의 재시도 로직은 어떻게 구현하기로 했지?"
}
```

**Response (200 OK):**
```json
{
  "id": "msg_abc123",
  "message": "결제 취소 API의 재시도 로직은 어떻게 구현하기로 했지?",
  "response": "2024-10-15 기술 리뷰 미팅 노트에 따르면, 결제 취소 API는 최대 3회 재시도하며...",
  "sources": [
    {
      "document_id": "doc_xyz789",
      "filename": "기술리뷰_20241015.pdf",
      "page": 3,
      "snippet": "재시도 로직은 exponential backoff를 사용하여..."
    }
  ],
  "created_at": "2025-12-20T12:00:00Z"
}
```

### 채팅 히스토리 조회

```
GET /channels/{channel_id}/chat/history
```

**Query Parameters:**
| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| limit | int | 50 | 최대 조회 개수 |

**Response (200 OK):**
```json
{
  "messages": [
    {
      "id": "msg_abc123",
      "role": "user",
      "content": "결제 취소 API의 재시도 로직은?",
      "created_at": "2025-12-20T12:00:00Z"
    },
    {
      "id": "msg_abc124",
      "role": "assistant",
      "content": "2024-10-15 기술 리뷰 미팅 노트에 따르면...",
      "sources": [...],
      "created_at": "2025-12-20T12:00:01Z"
    }
  ]
}
```

---

## 에러 응답

### 형식

```json
{
  "error": {
    "code": "CHANNEL_NOT_FOUND",
    "message": "채널을 찾을 수 없습니다",
    "details": {}
  }
}
```

### 에러 코드

| HTTP 상태 | 코드 | 설명 |
|----------|------|------|
| 400 | INVALID_REQUEST | 잘못된 요청 |
| 404 | CHANNEL_NOT_FOUND | 채널 없음 |
| 404 | DOCUMENT_NOT_FOUND | 문서 없음 |
| 413 | FILE_TOO_LARGE | 파일 크기 초과 (100MB) |
| 415 | UNSUPPORTED_FILE_TYPE | 지원하지 않는 파일 형식 |
| 429 | RATE_LIMIT_EXCEEDED | 요청 한도 초과 |
| 500 | INTERNAL_ERROR | 서버 내부 오류 |

---

## 지원 파일 형식

| 카테고리 | 확장자 |
|---------|--------|
| 문서 | .pdf, .docx, .pptx, .xlsx |
| 텍스트 | .txt, .md, .html |
| 데이터 | .json, .csv, .xml |
| 코드 | .py, .js, .java, .cpp |

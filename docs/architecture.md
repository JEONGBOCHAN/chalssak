# 시스템 아키텍처

## 프로젝트 개요

**목표**: Gemini File Search API를 활용하여 채널별로 격리된 문서 검색 및 질의응답(RAG) 시스템 구축

**핵심 컨셉**: NotebookLM 클론 - 문서 기반 AI 어시스턴트

## 전체 구조

```
┌─────────────────────────────────────────────────────────────────┐
│                         사용자                                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI 서버                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ 채널 관리    │  │ 파일 업로드  │  │ 질의응답     │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ 용량 관리    │  │ 스케줄러    │  │ 관리자 통계  │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      LangGraph 워크플로우                         │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐      │
│  │ 입력     │ -> │ 검색    │ -> │ 컨텍스트 │ -> │ 응답생성 │      │
│  │ 처리     │    │         │    │ 구성     │    │         │      │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘      │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────┐
│    Gemini File Search   │     │      SQLite (Local)     │
│  ┌───────────────────┐  │     │  ┌───────────────────┐  │
│  │ Store A (채널1)    │  │     │  │ 채널 메타데이터    │  │
│  │ Store B (채널2)    │  │     │  │ 채팅 히스토리      │  │
│  │ Store C (채널3)    │  │     │  │ 용량 추적         │  │
│  └───────────────────┘  │     │  └───────────────────┘  │
└─────────────────────────┘     └─────────────────────────┘
```

## 핵심 개념

### 채널 (Channel)

- 문서를 그룹화하는 단위
- 1 채널 = 1 Gemini File Search Store
- 채널 간 컨텍스트 격리

### 문서 (Document)

- 채널에 업로드되는 파일
- 지원 형식: PDF, DOCX, TXT, MD, CSV 등
- 최대 100MB/파일

### 질의응답 (Q&A)

- 채널 내 문서를 기반으로 RAG 수행
- 출처(grounding) 정보 포함 응답

### 생애주기 관리

- 채널 활성/비활성 상태 추적
- 비활성 채널 자동 정리 (스케줄러)
- 용량 제한 및 모니터링

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| API 서버 | FastAPI |
| 워크플로우 | LangGraph 1.0 |
| RAG 엔진 | Gemini File Search API |
| LLM | Gemini 2.5 Flash |
| 로컬 DB | SQLite + SQLAlchemy |
| 스케줄러 | APScheduler |
| 언어 | Python 3.11+ |
| 테스트 | pytest |

## 디렉토리 구조

```
docuchat/
├── docs/                    # 개발 문서
│   ├── README.md
│   ├── architecture.md      # 이 문서
│   ├── api-spec.md
│   ├── setup.md
│   └── development.md
├── src/                     # 소스 코드
│   ├── api/                 # FastAPI 라우터
│   │   └── v1/
│   │       ├── router.py    # 라우터 통합
│   │       ├── channels.py
│   │       ├── documents.py
│   │       ├── chat.py
│   │       ├── capacity.py
│   │       ├── admin.py
│   │       ├── scheduler.py
│   │       └── health.py
│   ├── core/                # 핵심 설정
│   │   ├── config.py
│   │   └── database.py
│   ├── models/              # Pydantic 모델
│   │   ├── channel.py
│   │   ├── document.py
│   │   ├── chat.py
│   │   └── capacity.py
│   ├── services/            # 비즈니스 로직
│   │   ├── gemini.py        # Gemini API 클라이언트
│   │   ├── crawler.py       # URL 크롤러
│   │   ├── channel_repository.py
│   │   ├── capacity_service.py
│   │   ├── lifecycle_policy.py
│   │   ├── admin_stats.py
│   │   ├── api_metrics.py
│   │   └── scheduler.py
│   ├── workflows/           # LangGraph 워크플로우
│   │   └── rag.py
│   └── main.py              # 앱 진입점
├── tests/                   # 테스트
│   ├── api/v1/
│   ├── services/
│   └── conftest.py
├── poc/                     # POC 코드
├── .env                     # 환경변수 (Git 제외)
├── .gitignore
├── requirements.txt
└── CLAUDE.md                # Claude Code 지침
```

## 마일스톤

| Phase | 목표 | 상태 |
|-------|------|------|
| 1 | API 분석 및 POC | ✅ 완료 |
| 2 | 핵심 백엔드 구현 | ✅ 완료 |
| 3 | 채널 생애주기 관리 | ✅ 완료 |
| 4 | 확장 기능 (옵션) | 백로그 |

## 데이터 흐름

### 채널 생성

```
사용자 요청 -> FastAPI -> GeminiService -> Gemini API (Store 생성)
                      -> ChannelRepository -> SQLite (메타데이터 저장)
```

### 파일 업로드

```
파일 업로드 -> FastAPI -> CapacityService (용량 검증)
                      -> GeminiService -> Gemini API (Store에 import)
                      -> ChannelRepository -> SQLite (용량 업데이트)
```

### URL 업로드

```
URL 요청 -> FastAPI -> CrawlerService (크롤링 + 마크다운 변환)
                    -> GeminiService -> Gemini API (업로드)
```

### 질의응답

```
질문 -> FastAPI -> LangGraph 워크플로우 -> GeminiService (검색 + 생성)
               -> ChatHistoryRepository -> SQLite (히스토리 저장)
```

### 비활성 채널 정리 (스케줄러)

```
APScheduler (매일 00:00) -> LifecyclePolicy (비활성 감지)
                        -> GeminiService (Store 삭제)
                        -> ChannelRepository (메타데이터 삭제)
```

## 제약사항

| 항목 | 제한 |
|------|------|
| 파일 크기 | 최대 100MB |
| 채널당 파일 수 | 최대 50개 (설정 가능) |
| 채널당 용량 | 최대 100MB (설정 가능) |
| 저장소 용량 (Free) | 1GB |
| 저장소 용량 (권장) | 20GB 이하/Store |
| 쿼리당 Store | 최대 5개 |
| 비활성 기준 | 90일 미접근 |

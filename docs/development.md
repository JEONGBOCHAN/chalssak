# 개발 가이드

## 개발 방식

**바이브 코딩**: Claude Code가 개발, 사용자는 검수

- Claude Code가 코드 작성
- 사용자가 방향 제시 및 검수
- 자동화 가능한 작업은 Claude에게 위임
- Linear로 작업 관리

## 코드 컨벤션

### Python 스타일

- PEP 8 준수
- 타입 힌트 사용
- Docstring 작성 (Google 스타일)

```python
def create_channel(name: str, description: str | None = None) -> Channel:
    """채널을 생성합니다.

    Args:
        name: 채널 이름
        description: 채널 설명 (선택)

    Returns:
        생성된 Channel 객체

    Raises:
        ValueError: 이름이 비어있는 경우
    """
    pass
```

### 네이밍 규칙

| 대상 | 규칙 | 예시 |
|------|------|------|
| 변수/함수 | snake_case | `channel_name`, `create_store` |
| 클래스 | PascalCase | `ChannelService`, `DocumentUploader` |
| 상수 | UPPER_SNAKE | `MAX_FILE_SIZE`, `API_VERSION` |
| 파일 | snake_case | `channel_service.py` |

### 디렉토리 규칙

```
src/
├── api/          # FastAPI 라우터 (엔드포인트 정의)
├── core/         # 설정, 의존성 주입
├── services/     # 비즈니스 로직
├── workflows/    # LangGraph 워크플로우
└── models/       # Pydantic 모델
```

## Git 워크플로우

### 브랜치 전략

```
main (배포)
  └── develop (개발)
        ├── feature/채널-생성
        ├── feature/파일-업로드
        └── fix/인코딩-오류
```

### 커밋 메시지

```
<타입>: <제목>

<본문 (선택)>
```

**타입:**
- `feat`: 새 기능
- `fix`: 버그 수정
- `docs`: 문서
- `refactor`: 리팩토링
- `test`: 테스트
- `chore`: 기타

**예시:**
```
feat: 채널 생성 API 구현

- POST /channels 엔드포인트 추가
- ChannelService.create_channel() 구현
- Gemini File Search Store 연동
```

## 테스트

### 테스트 실행

```bash
# 전체 테스트
pytest

# 특정 파일
pytest tests/test_channel.py

# 커버리지
pytest --cov=src
```

### 테스트 구조

```python
# tests/test_channel_service.py

def test_create_channel_success():
    """채널 생성 성공 케이스"""
    service = ChannelService()
    channel = service.create_channel("테스트 채널")

    assert channel.name == "테스트 채널"
    assert channel.store_name is not None


def test_create_channel_empty_name():
    """빈 이름으로 채널 생성 시 에러"""
    service = ChannelService()

    with pytest.raises(ValueError):
        service.create_channel("")
```

## Phase별 작업

### Phase 1: POC (완료)

- [x] Gemini File Search API 분석
- [x] POC 코드 작성
- [x] 테스트 성공

### Phase 2: 핵심 백엔드

- [ ] FastAPI 프로젝트 구조 생성
- [ ] LangGraph 워크플로우 설계
- [ ] 채널 CRUD API 구현
- [ ] 문서 업로드 API 구현
- [ ] 채팅 API 구현

### Phase 3: 리소스 관리

- [ ] 채널 생애주기 정책
- [ ] 용량 제한 구현
- [ ] 비활성 채널 자동 정리

### Phase 4: 확장 (옵션)

- [ ] 추가 기능 기획
- [ ] 구현 및 검증

## Linear 연동

### 이슈 생성

```
CHA-{번호}: {제목}

예: CHA-5: 채널 생성 API 구현
```

### 이슈 상태

- `Todo`: 시작 전
- `In Progress`: 작업 중
- `Done`: 완료

## 참고 자료

- [Gemini File Search API 문서](https://ai.google.dev/gemini-api/docs/file-search)
- [FastAPI 문서](https://fastapi.tiangolo.com/)
- [LangGraph 문서](https://langchain-ai.github.io/langgraph/)
- [Linear 프로젝트](https://linear.app/chalssak/project/노트북-lm-클론-코딩-a0f53b8e2e10)

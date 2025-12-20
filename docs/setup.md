# 환경 설정

## 요구사항

| 항목 | 버전 |
|------|------|
| Python | 3.11+ (현재: 3.14.0) |
| pip | 최신 |
| Git | 최신 |

## 1. 프로젝트 클론

```bash
git clone <repository-url>
cd chalssak
```

## 2. 가상환경 생성 (권장)

```bash
# 가상환경 생성
python -m venv venv

# 활성화 (Windows)
venv\Scripts\activate

# 활성화 (Mac/Linux)
source venv/bin/activate
```

## 3. 의존성 설치

```bash
pip install -r requirements.txt
```

## 4. 환경변수 설정

`.env` 파일 생성:

```bash
# .env
GOOGLE_API_KEY=your_api_key_here
```

### API 키 발급 방법

1. [Google AI Studio](https://aistudio.google.com/apikey) 접속
2. Google 계정으로 로그인
3. "API 키 만들기" 클릭
4. 생성된 키를 `.env` 파일에 복사

## 5. 실행 확인

### POC 테스트

```bash
python poc/file_search_poc.py "테스트파일.pdf" "이 문서의 요약은?"
```

### 서버 실행 (Phase 2 이후)

```bash
uvicorn src.main:app --reload
```

## 디렉토리 구조

```
chalssak/
├── .env                 # 환경변수 (Git 제외)
├── .gitignore           # Git 제외 목록
├── requirements.txt     # Python 의존성
├── CLAUDE.md            # Claude Code 지침
├── docs/                # 개발 문서
├── poc/                 # POC 코드
├── src/                 # 소스 코드 (Phase 2)
└── tests/               # 테스트 (Phase 2)
```

## 의존성 목록

```
# requirements.txt
google-genai>=1.0.0      # Gemini API SDK
python-dotenv>=1.0.0     # 환경변수 로드
requests>=2.28.0         # HTTP 요청

# Phase 2에서 추가 예정
# fastapi>=0.100.0
# uvicorn>=0.23.0
# langgraph>=1.0.0
# pytest>=7.0.0
```

## 문제 해결

### API 키 오류

```
ValueError: GOOGLE_API_KEY가 .env에 설정되지 않았습니다
```

**해결**: `.env` 파일에 API 키가 올바르게 설정되었는지 확인

### 인코딩 오류 (Windows)

```
UnicodeEncodeError: 'cp949' codec can't encode character
```

**해결**: 코드에서 UTF-8 인코딩 설정 확인
```python
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
```

### 모듈 없음 오류

```
ModuleNotFoundError: No module named 'google.genai'
```

**해결**: 의존성 재설치
```bash
pip install -r requirements.txt
```

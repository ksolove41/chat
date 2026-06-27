# 💬 프로젝트 대화 로그방

내부망 환경에서 프로젝트별 대화 로그를 남기기 위한 Streamlit 기반 채팅 앱입니다.

## 주요 기능

- 채팅방 생성 / 삭제
- 참여자 관리 (참여 / 나가기 / 강퇴)
- 메시지 전송 및 이미지 첨부
- 대화 내용 검색
- 대화 로그 JSON 다운로드
- 약 2초마다 자동 갱신
- 관리자 전용 기능 (방 삭제, 사용자 강퇴)

## 기술 스택

| 항목 | 내용 |
|---|---|
| 언어 | Python 3.x |
| 프레임워크 | Streamlit |
| 데이터 저장 | JSON 파일 |

## 설치 및 실행

```bash
# 의존성 설치
pip install -r requirements.txt

# 앱 실행
streamlit run chat.py
```

브라우저에서 `http://localhost:8501` 로 접속합니다.

## 관리자 설정

[chat.py](chat.py) 상단의 `ADMIN_NAME` 값을 본인 이름으로 변경하세요.

```python
ADMIN_NAME = "김시온"
```

화면의 **내 이름 입력**에 동일하게 입력하면 관리자 권한이 활성화됩니다.

## 프로젝트 구조

```
chat/
├── chat.py            # 메인 앱
├── requirements.txt   # 의존성
├── .gitignore
└── README.md
```

> `chat_rooms.json`, `chat_messages.json`, `chat_uploads/` 는 실행 시 자동 생성되며 `.gitignore` 에 포함되어 있습니다.

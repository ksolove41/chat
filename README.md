# 💬 프로젝트 대화 로그방

내부망 환경에서 프로젝트별 대화 로그를 남기기 위한 Streamlit 기반 채팅 앱입니다.

## 주요 기능

- 채팅방 생성 / 삭제
- 참여자 관리 (참여 / 나가기 / 강퇴)
- 메시지 전송 및 이미지 첨부
- 대화 내용 검색
- 대화 로그 JSON 다운로드 (id · 일시 · 방이름 · 작성자 · 메시지 5개 필드)
- 약 2초마다 자동 갱신
- 관리자 전용 기능 (방 삭제, 사용자 강퇴)
- **이모지 반응** — 각 메시지에 👌 / 👍 / 😭 / ✅ 반응 추가 (인원 수 표시)
- **읽음 표시** — 메시지를 본 인원 수를 👁️ 로 표시
- **이름 자동 유지** — 이름 설정 후 새로고침해도 재입력 불필요 (URL 파라미터 저장)
- **이슈 자동 등록** — 메시지에 `이슈제목:` 과 `재현경로:` 를 포함하면 결함 핵심 요약에 자동 등록
- **등록 결함 핵심 요약** — 방별 이슈 목록을 최신순으로 상단에 표시

## 기술 스택

| 항목 | 내용 |
|---|---|
| 언어 | Python 3.x |
| 프레임워크 | Streamlit |
| 데이터 저장 | JSON 파일 |
| 데스크톱 창 | pywebview (Edge WebView2) |

## 실행 방법

### 방법 1 — 데스크톱 앱으로 실행 (권장)

팀원들이 브라우저 없이 전용 앱 창에서 채팅합니다.

#### 서버 PC (1대)

```bash
# 의존성 설치
pip install -r requirements.txt

# 서버 실행 (앱 창 + Streamlit 자동 시작)
python server_launcher.py
```

앱 창 제목에 **서버 IP** 가 표시됩니다. 이 IP를 팀원에게 공유하세요.

#### 클라이언트 PC (팀원 각자)

```bash
# 클라이언트 실행
python client_launcher.py
```

최초 실행 시 서버 IP 입력 팝업이 뜹니다. 이후에는 자동 접속됩니다.

---

### 방법 2 — exe 빌드 후 배포

Python이 없는 PC에도 배포 가능합니다.

```bash
# 빌드 도구 설치
pip install pyinstaller

# 빌드 실행 (build.bat 더블클릭 또는 아래 명령)
build.bat
```

빌드 결과물 (`dist\` 폴더):

| 파일 | 배포 대상 | 비고 |
|---|---|---|
| `server.exe` | 서버 PC | `chat.py` 와 같은 폴더에 둘 것 |
| `client.exe` | 팀원 PC | 단독 실행, Python 불필요 |

---

### 방법 3 — 브라우저로 직접 접속

```bash
pip install -r requirements.txt
streamlit run chat.py
```

브라우저에서 `http://localhost:8501` 로 접속합니다.

## 관리자 설정

[chat.py](chat.py) 상단의 `ADMIN_NAME` 값을 본인 이름으로 변경하세요.

```python
ADMIN_NAME = "김시온"
```

화면의 **내 이름 입력**에 동일하게 입력하면 관리자 권한이 활성화됩니다.

## 이슈 등록 방법

메시지에 아래 두 키워드를 포함하면 자동으로 결함 요약에 등록됩니다.

```
이슈제목: 로그인 버튼이 동작하지 않음
재현경로: 홈 > 로그인 > 계정 입력 후 버튼 클릭
```

## 프로젝트 구조

```
chat/
├── chat.py                # 메인 앱
├── server_launcher.py     # 서버 실행 런처
├── client_launcher.py     # 클라이언트 접속 런처
├── build.bat              # exe 빌드 스크립트
├── requirements.txt       # 의존성
├── .gitignore
└── README.md
```

> 아래 파일들은 실행 시 자동 생성되며 `.gitignore` 에 포함되어 있습니다.
>
> | 파일 | 내용 |
> |---|---|
> | `chat_messages.json` | 메시지 로그 (id · 일시 · 방이름 · 작성자 · 메시지) |
> | `chat_meta.json` | 반응 · 읽음 · 첨부파일 메타 통합 저장 |
> | `chat_rooms.json` | 채팅방 목록 |
> | `chat_issues.json` | 자동 등록된 이슈 목록 |
> | `chat_uploads/` | 첨부 이미지 파일 |
> | `chat_config.json` | 클라이언트 서버 IP 설정 |

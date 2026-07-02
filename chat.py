import streamlit as st
from pathlib import Path
from datetime import datetime
import html
import re
import uuid
import json


# ═══════════════════════════════════════════
# 설정
# ═══════════════════════════════════════════
ADMIN_NAME   = "김시온"
ROOM_FILE    = Path("chat_rooms.json")
MESSAGE_FILE = Path("chat_messages.json")  # 5개 필드만
META_FILE    = Path("chat_meta.json")      # 반응·읽음·첨부 통합 {msg_id: {...}}
ISSUE_FILE   = Path("chat_issues.json")
UPLOAD_DIR   = Path("chat_uploads")

IMAGE_TYPES = ["png", "jpg", "jpeg", "gif", "webp"]

REACTION_TYPES = [
    ("OK",   "\U0001f44c"),
    ("따봉", "\U0001f44d"),
    ("cry",  "\U0001f62d"),
    ("chk",  "✅"),
]
REACTION_KEYS = [rt[0] for rt in REACTION_TYPES]

LOG_FIELDS = ["id", "일시", "방이름", "작성자", "메시지"]


# ═══════════════════════════════════════════
# JSON 유틸
# ═══════════════════════════════════════════
def _load_list(path):
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_list(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _load_dict(path):
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_dict(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def init_json_files():
    UPLOAD_DIR.mkdir(exist_ok=True)
    for f in [ROOM_FILE, MESSAGE_FILE, ISSUE_FILE]:
        if not f.exists():
            _save_list(f, [])
    if not META_FILE.exists():
        _save_dict(META_FILE, {})


# ─── 메시지 ───────────────────────────────
def _normalize_message(row):
    if not isinstance(row, dict):
        return None
    return {
        "id":     str(row.get("id") or uuid.uuid4()),
        "일시":   str(row.get("일시", "")),
        "방이름": str(row.get("방이름", "")),
        "작성자": str(row.get("작성자", "")),
        "메시지": str(row.get("메시지", "")),
    }


def load_messages():
    init_json_files()
    return [m for m in (_normalize_message(r) for r in _load_list(MESSAGE_FILE)) if m]


def save_messages(messages):
    _save_list(MESSAGE_FILE, [{k: m[k] for k in LOG_FIELDS if k in m} for m in messages])


# ─── 메타 (반응 + 읽음 + 첨부) ────────────
def load_meta():
    return _load_dict(META_FILE)


def save_meta(data):
    _save_dict(META_FILE, data)


def get_msg_meta(meta, msg_id):
    return meta.get(msg_id, {
        "reactions": {k: [] for k in REACTION_KEYS},
        "reads": [],
        "attach_name": "",
        "attach_path": "",
        "attach_type": "",
    })


# ─── 방 ──────────────────────────────────
def _normalize_rooms(rows):
    result = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        result.append({
            "방이름":   str(row.get("방이름", "")),
            "생성일시": str(row.get("생성일시", "")),
            "참여자":   str(row.get("참여자", "")),
        })
    return result


def load_rooms():
    init_json_files()
    return _normalize_rooms(_load_list(ROOM_FILE))


def save_rooms(rooms):
    _save_list(ROOM_FILE, _normalize_rooms(rooms))


# ─── 이슈 ────────────────────────────────
def load_issues():
    return _load_list(ISSUE_FILE)


def save_issues(issues):
    _save_list(ISSUE_FILE, issues)


# ─── 다운로드 ─────────────────────────────
def make_json_download(data):
    return json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")


# ═══════════════════════════════════════════
# 유틸리티
# ═══════════════════════════════════════════
def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def safe_text(value):
    return html.escape(str(value))


def split_participants(text):
    if not text:
        return []
    return [x.strip() for x in str(text).split(",") if x.strip()]


def join_participants(names):
    seen = []
    for name in names:
        name = str(name).strip()
        if name and name not in seen:
            seen.append(name)
    return ", ".join(seen)


def is_admin():
    return st.session_state.get("user_name", "").strip() == ADMIN_NAME


def sanitize_filename(filename):
    return re.sub(r'[\\/:*?"<>|]', "_", filename.strip())


def save_uploaded_image(uploaded_file):
    if uploaded_file is None:
        return "", "", ""
    original_name = sanitize_filename(uploaded_file.name)
    ext = original_name.split(".")[-1].lower()
    if ext not in IMAGE_TYPES:
        return "", "", ""
    saved_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}_{original_name}"
    saved_path = UPLOAD_DIR / saved_name
    with open(saved_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return original_name, str(saved_path), ext


def parse_issue_from_message(message):
    if "이슈제목" not in message or "재현경로" not in message:
        return None
    title = repro = ""
    for line in message.split("\n"):
        m = re.search(r'이슈제목\s*[:\s]\s*(.*)', line)
        if m:
            title = m.group(1).strip()
        m = re.search(r'재현경로\s*[:\s]\s*(.*)', line)
        if m:
            repro = m.group(1).strip()
    return (title, repro) if (title or repro) else None


# ═══════════════════════════════════════════
# 방 기능
# ═══════════════════════════════════════════
def create_room(room_name):
    rooms = load_rooms()
    if any(r["방이름"] == room_name for r in rooms):
        return False, "이미 같은 이름의 방이 있어요."
    rooms.append({"방이름": room_name, "생성일시": now_text(), "참여자": ""})
    save_rooms(rooms)
    return True, "방을 만들었어요."


def delete_room(room_name):
    rooms    = load_rooms()
    messages = load_messages()
    msg_ids  = {m["id"] for m in messages if m["방이름"] == room_name}

    save_rooms([r for r in rooms if r["방이름"] != room_name])
    save_messages([m for m in messages if m["방이름"] != room_name])
    save_issues([i for i in load_issues() if i.get("방이름") != room_name])

    if msg_ids:
        meta = {k: v for k, v in load_meta().items() if k not in msg_ids}
        # 첨부 파일도 삭제
        for mid in msg_ids:
            p = Path(load_meta().get(mid, {}).get("attach_path", ""))
            try:
                if p.exists():
                    p.unlink()
            except Exception:
                pass
        save_meta(meta)


def join_room(room_name, user_name):
    rooms = load_rooms()
    for room in rooms:
        if room["방이름"] == room_name:
            participants = split_participants(room["참여자"])
            if user_name not in participants:
                participants.append(user_name)
            room["참여자"] = join_participants(participants)
            break
    save_rooms(rooms)


def leave_room(room_name, user_name):
    rooms = load_rooms()
    for room in rooms:
        if room["방이름"] == room_name:
            room["참여자"] = join_participants(
                [p for p in split_participants(room["참여자"]) if p != user_name]
            )
            break
    save_rooms(rooms)


def get_room_participants(room_name):
    for room in load_rooms():
        if room["방이름"] == room_name:
            return split_participants(room["참여자"])
    return []


# ═══════════════════════════════════════════
# 메시지 기능
# ═══════════════════════════════════════════
def add_message(room_name, user_name, message, uploaded_file=None):
    msg_id = str(uuid.uuid4())
    ts     = now_text()

    messages = load_messages()
    messages.append({"id": msg_id, "일시": ts, "방이름": room_name, "작성자": user_name, "메시지": message})
    save_messages(messages)

    attach_name, attach_path, attach_type = save_uploaded_image(uploaded_file)
    meta = load_meta()
    meta[msg_id] = {
        "reactions":   {k: [] for k in REACTION_KEYS},
        "reads":       [user_name],
        "attach_name": attach_name,
        "attach_path": attach_path,
        "attach_type": attach_type,
    }
    save_meta(meta)

    parsed = parse_issue_from_message(message)
    if parsed:
        title, repro = parsed
        issues = load_issues()
        issues.append({
            "id": str(uuid.uuid4()), "방이름": room_name, "메시지_id": msg_id,
            "이슈제목": title, "재현경로": repro, "작성자": user_name, "일시": ts,
        })
        save_issues(issues)


def toggle_reaction(msg_id, reaction_key, user_name):
    meta  = load_meta()
    entry = get_msg_meta(meta, msg_id)
    users = list(entry["reactions"].get(reaction_key, []))
    if user_name in users:
        users.remove(user_name)
    else:
        users.append(user_name)
    entry["reactions"][reaction_key] = users
    meta[msg_id] = entry
    save_meta(meta)


def mark_messages_read(room_name, user_name):
    messages = load_messages()
    meta     = load_meta()
    changed  = False
    for msg in messages:
        if msg["방이름"] != room_name:
            continue
        mid   = msg["id"]
        entry = get_msg_meta(meta, mid)
        if user_name not in entry["reads"]:
            entry["reads"].append(user_name)
            meta[mid] = entry
            changed = True
    if changed:
        save_meta(meta)


# ═══════════════════════════════════════════
# 자동 스크롤
# ═══════════════════════════════════════════
def scroll_chat_to_bottom(nonce=""):
    st.html(f"""<!-- nonce:{nonce} -->
<script>
function scrollChatToBottom() {{
    const anchor = document.getElementById("chat-bottom-anchor");
    if (anchor) {{
        let el = anchor.parentElement;
        while (el) {{
            const s = getComputedStyle(el);
            if ((s.overflowY==="auto"||s.overflowY==="scroll"||s.overflowY==="overlay")
                && el.scrollHeight > el.clientHeight) {{
                el.scrollTop = el.scrollHeight; return;
            }}
            el = el.parentElement;
        }}
    }}
    const areas = Array.from(document.querySelectorAll("div")).filter(el=>{{
        const s=getComputedStyle(el);
        return el.scrollHeight>el.clientHeight
            && (s.overflowY==="auto"||s.overflowY==="scroll"||s.overflowY==="overlay")
            && el.clientHeight>=400 && el.clientHeight<=700;
    }});
    if (areas.length>0) areas[areas.length-1].scrollTop = areas[areas.length-1].scrollHeight;
}}
setTimeout(scrollChatToBottom,100);
setTimeout(scrollChatToBottom,400);
setTimeout(scrollChatToBottom,900);
</script>""")


# ═══════════════════════════════════════════
# 페이지 설정 & 스타일
# ═══════════════════════════════════════════
st.set_page_config(page_title="프로젝트 대화 로그방", page_icon="\U0001f4ac", layout="wide")

st.markdown("""
<style>
html, body, [class*="css"] {
    font-family: "Gungsuh", "궁서", serif !important;
    font-weight: 700 !important;
}
.stButton button {
    font-weight: 900 !important;
    border-radius: 14px !important;
    padding: 0.35rem 0.6rem !important;
}
.chat-left {
    max-width: 75%;
    border: 1px solid #ddd;
    border-radius: 16px;
    padding: 10px 14px;
    margin: 4px 0 0 0;
}
.chat-right {
    max-width: 75%;
    border: 1px solid #999;
    border-radius: 16px;
    padding: 10px 14px;
    margin: 4px 0 0 auto;
}
.chat-meta { font-size: 12px; color: #666; margin-bottom: 5px; }
.chat-message { font-size: 16px; white-space: pre-wrap; line-height: 1.45; }
.issue-badge {
    display: inline-block;
    border: 1px solid #ff6b6b88;
    border-radius: 8px;
    padding: 1px 7px;
    font-size: 11px;
    color: #ff6b6b;
    margin-top: 5px;
}
.read-badge { font-size: 11px; color: #aaa; padding: 2px 0; }
.room-title { font-size: 26px; font-weight: 900; margin-bottom: 4px; }
.small-guide { font-size: 13px; color: #777; margin-bottom: 12px; }
.summary-box {
    border: 1px solid rgba(255,107,107,0.35);
    border-radius: 12px;
    padding: 10px 14px;
    margin-bottom: 8px;
    background: rgba(255,107,107,0.05);
    line-height: 1.65;
    font-size: 15px;
}
div[data-testid="stTextInput"] input { font-weight: 800 !important; }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════
# 세션 초기화
# ═══════════════════════════════════════════
init_json_files()

if "user_name" not in st.session_state:
    st.session_state.user_name = st.query_params.get("user", "")
if "pending_user_name" not in st.session_state:
    st.session_state.pending_user_name = st.session_state.user_name
if "selected_room" not in st.session_state:
    st.session_state.selected_room = ""
if "message_box_key" not in st.session_state:
    st.session_state.message_box_key = 0
if "image_box_key" not in st.session_state:
    st.session_state.image_box_key = 0


st.title("\U0001f4ac 프로젝트 대화 로그방")
st.caption("내부망에서 프로젝트별 대화 로그를 남기기 위한 Streamlit + JSON 기반 프로토타입")


# ═══════════════════════════════════════════
# 자동 갱신 대화 로그 (Fragment)
# ═══════════════════════════════════════════
@st.fragment(run_every="2s")
def render_chat_log(selected_room, search_keyword, current_user):
    messages = load_messages()
    room_msgs = [m for m in messages if m["방이름"] == selected_room]
    st.html(f'<script>window.parent.postMessage({{type:"chatMsgCount",count:{len(room_msgs)}}},"*")</script>')

    if search_keyword.strip():
        kw = search_keyword.strip().lower()
        room_msgs = [m for m in room_msgs
                     if kw in m.get("메시지", "").lower() or kw in m.get("작성자", "").lower()]

    st.subheader("\U0001f4dc 대화 로그")
    st.caption("약 2초마다 자동으로 새 메시지를 확인해요.")

    if not room_msgs:
        st.info("아직 대화가 없어.")
        return

    room_msgs = sorted(room_msgs, key=lambda x: x.get("일시", ""))
    all_meta  = load_meta()
    n = len(REACTION_TYPES)

    with st.container(height=520):
        for row in room_msgs:
            writer       = row.get("작성자", "")
            is_mine      = writer == current_user
            css_class    = "chat-right" if is_mine else "chat-left"
            msg_id       = row.get("id", "")
            message_text = row.get("메시지", "").strip()
            entry        = get_msg_meta(all_meta, msg_id)
            reactions    = entry["reactions"]
            read_count   = len(entry["reads"])
            attach_name  = entry.get("attach_name", "")
            attach_path  = entry.get("attach_path", "")

            is_issue    = "이슈제목" in message_text and "재현경로" in message_text
            issue_badge = '<br><span class="issue-badge">\U0001f41b 이슈 등록됨</span>' if is_issue else ""

            st.html(f"""
            <div class="{css_class}">
                <div class="chat-meta">\U0001f552 {safe_text(row.get("일시",""))} · \U0001f464 {safe_text(writer)}</div>
                <div class="chat-message">{safe_text(message_text)}</div>
                {issue_badge}
            </div>
            """)

            if attach_path and Path(attach_path).exists():
                st.image(attach_path, caption=f"\U0001f5bc️ {attach_name}", width=320)
            elif attach_name:
                st.warning(f"첨부 이미지를 찾을 수 없어: {attach_name}")

            if is_mine:
                all_cols = st.columns([3, 1] + [1] * n)
                col_read = all_cols[1]
                r_cols   = all_cols[2:]
            else:
                all_cols = st.columns([1] * n + [1, 3])
                r_cols   = all_cols[:n]
                col_read = all_cols[n]

            with col_read:
                if read_count > 0:
                    st.html(f'<div class="read-badge">\U0001f441️ {read_count}</div>')

            for i, (key, emoji) in enumerate(REACTION_TYPES):
                users = reactions.get(key, [])
                label = f"{emoji} {len(users)}" if users else emoji
                with r_cols[i]:
                    if st.button(label, key=f"react_{key}_{msg_id}"):
                        if current_user:
                            toggle_reaction(msg_id, key, current_user)
                            mark_messages_read(selected_room, current_user)
                            st.rerun()

        st.markdown('<div id="chat-bottom-anchor"></div>', unsafe_allow_html=True)

    if not search_keyword.strip():
        last_id = room_msgs[-1].get("id", "") if room_msgs else "empty"
        scroll_chat_to_bottom(nonce=f"{len(room_msgs)}_{last_id}")


# ═══════════════════════════════════════════
# 레이아웃
# ═══════════════════════════════════════════
left, right = st.columns([1, 2])

with left:
    st.subheader("\U0001f64b 내 정보")

    name_col, button_col = st.columns([3, 1])
    with name_col:
        st.text_input("내 이름 입력", placeholder="본인 이름", key="pending_user_name")
    with button_col:
        st.write("")
        if st.button("설정 완료", use_container_width=True):
            entered = st.session_state.pending_user_name.strip()
            if not entered:
                st.warning("이름을 입력해줘.")
            else:
                st.session_state.user_name = entered
                st.query_params["user"] = entered
                st.success(f"{entered} 님으로 설정됐어요.")
                st.rerun()

    if st.session_state.user_name:
        st.info(f"현재 이름: **{st.session_state.user_name}**")
    if is_admin():
        st.success("\U0001f6e1️ 관리자 모드입니다.")

    st.divider()

    st.subheader("\U0001f331 새 방 만들기")
    new_room_name = st.text_input("새 방 이름 입력", placeholder="예: AI Agent QA 프로젝트")
    if st.button("\U0001f331 방 만들기", use_container_width=True):
        if not new_room_name.strip():
            st.warning("방 이름을 입력해줘.")
        else:
            ok, msg = create_room(new_room_name.strip())
            if ok:
                st.success(msg)
                st.session_state.selected_room = new_room_name.strip()
                st.rerun()
            else:
                st.warning(msg)

    st.divider()

    st.subheader("\U0001f6aa 대화방 목록")
    rooms      = load_rooms()
    room_names = [r["방이름"] for r in rooms]

    if not room_names:
        st.info("아직 만들어진 방이 없어.")
    else:
        for rn in room_names:
            label = f"✅ {rn}" if st.session_state.selected_room == rn else f"\U0001f6aa {rn}"
            if st.button(label, key=f"room_{rn}", use_container_width=True):
                st.session_state.selected_room = rn
                if st.session_state.user_name:
                    mark_messages_read(rn, st.session_state.user_name)
                st.rerun()


with right:
    selected_room = st.session_state.selected_room

    if not selected_room:
        st.info("왼쪽에서 방을 만들거나 선택해줘.")
    else:
        st.html(f'<div class="room-title">\U0001f6aa 현재 방: {safe_text(selected_room)}</div>')
        st.html('<div class="small-guide">메시지를 입력하고 Enter를 누르거나, 오른쪽 \U0001f680 버튼을 누르면 바로 저장돼요.</div>')

        participants = get_room_participants(selected_room)
        with st.expander("\U0001f465 현재 방 참여자 보기", expanded=False):
            if participants:
                for person in participants:
                    col_name, col_kick = st.columns([5, 1])
                    with col_name:
                        prefix = "\U0001f6e1️" if person == ADMIN_NAME else "\U0001f464"
                        st.write(f"{prefix} {person}")
                    with col_kick:
                        if is_admin() and person != ADMIN_NAME:
                            if st.button("강퇴", key=f"kick_{selected_room}_{person}"):
                                leave_room(selected_room, person)
                                st.warning(f"{person} 님을 내보냈어요.")
                                st.rerun()
            else:
                st.caption("아직 참여자가 없어.")

            col_join, col_leave = st.columns(2)
            with col_join:
                if st.button("\U0001f91c 이 방 참여하기", use_container_width=True):
                    if not st.session_state.user_name:
                        st.warning("먼저 이름을 설정해줘.")
                    else:
                        join_room(selected_room, st.session_state.user_name)
                        st.success("참여했어요.")
                        st.rerun()
            with col_leave:
                if st.button("\U0001f44b 이 방 나가기", use_container_width=True):
                    if not st.session_state.user_name:
                        st.warning("먼저 이름을 설정해줘.")
                    else:
                        leave_room(selected_room, st.session_state.user_name)
                        st.success("나갔어요.")
                        st.rerun()

        if is_admin():
            with st.expander("\U0001f6e1️ 관리자 기능", expanded=False):
                delete_confirm = st.checkbox(f"'{selected_room}' 방 삭제 확인", key=f"del_{selected_room}")
                if st.button("\U0001f5d1️ 현재 방 삭제", use_container_width=True):
                    if not delete_confirm:
                        st.warning("삭제 확인 체크를 먼저 해줘.")
                    else:
                        delete_room(selected_room)
                        st.session_state.selected_room = ""
                        st.success("방과 로그를 삭제했어요.")
                        st.rerun()

        room_issues = [i for i in load_issues() if i.get("방이름") == selected_room]
        issue_count = len(room_issues)
        with st.expander(f"\U0001f525 등록 결함 핵심 요약 ({issue_count}건)", expanded=issue_count > 0):
            if not room_issues:
                st.caption("이 방에 등록된 이슈가 없어요.")
                st.caption("\U0001f4a1 메시지에 **이슈제목:** 과 **재현경로:** 를 포함하면 자동 등록돼요.")
            else:
                for idx, issue in enumerate(reversed(room_issues)):
                    num    = issue_count - idx
                    title  = safe_text(issue.get("이슈제목", "(제목 없음)"))
                    repro  = safe_text(issue.get("재현경로", "(경로 없음)"))
                    writer = safe_text(issue.get("작성자", ""))
                    dt     = safe_text(issue.get("일시", ""))
                    st.html(f"""
                    <div class="summary-box">
                        <strong>[{num}] {title}</strong><br>
                        재현경로: {repro}<br>
                        <span style="font-size:12px;color:#888;">\U0001f464 {writer} · \U0001f552 {dt}</span>
                    </div>
                    """)

        st.divider()

        search_keyword = st.text_input("\U0001f50e 대화 검색", placeholder="메시지, 작성자 검색")

        all_messages     = load_messages()
        room_messages_dl = [m for m in all_messages if m["방이름"] == selected_room]
        st.download_button(
            label="\U0001f4e5 현재 방 로그 JSON 다운로드",
            data=make_json_download(room_messages_dl),
            file_name=f"{selected_room}_대화로그.json",
            mime="application/json",
            use_container_width=True,
        )

        st.divider()

        render_chat_log(
            selected_room=selected_room,
            search_keyword=search_keyword,
            current_user=st.session_state.user_name,
        )

        st.divider()

        st.subheader("✍️ 메시지 작성")
        st.caption("\U0001f4a1 이슈 등록: 메시지에 **이슈제목:** 과 **재현경로:** 를 포함하면 이슈 요약에 자동 등록돼요.")

        with st.form("message_form", clear_on_submit=False):
            col_input, col_image, col_send = st.columns([7, 2, 1])
            with col_input:
                message = st.text_input(
                    "메시지 입력",
                    placeholder="메시지를 입력해줘.",
                    label_visibility="collapsed",
                    key=f"msg_{st.session_state.message_box_key}",
                )
            with col_image:
                uploaded_image = st.file_uploader(
                    "이미지",
                    type=IMAGE_TYPES,
                    label_visibility="collapsed",
                    key=f"img_{st.session_state.image_box_key}",
                )
            with col_send:
                submitted = st.form_submit_button("\U0001f680", use_container_width=True)

            if submitted:
                if not st.session_state.user_name:
                    st.warning("먼저 왼쪽에서 이름을 설정해줘.")
                elif not message.strip() and uploaded_image is None:
                    st.warning("메시지나 이미지를 입력해줘.")
                else:
                    join_room(selected_room, st.session_state.user_name)
                    add_message(
                        room_name=selected_room,
                        user_name=st.session_state.user_name,
                        message=message.strip(),
                        uploaded_file=uploaded_image,
                    )
                    mark_messages_read(selected_room, st.session_state.user_name)
                    st.session_state.message_box_key += 1
                    st.session_state.image_box_key   += 1
                    st.rerun()

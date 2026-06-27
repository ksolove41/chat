import streamlit as st
from pathlib import Path
from datetime import datetime
import html
import re
import uuid
import json

# =========================
# 관리자 설정
# =========================
# 김시온만 관리자 기능이 보임
ADMIN_NAME = "김시온"

# =========================
# 기본 설정
# =========================
ROOM_FILE = Path("chat_rooms.json")
MESSAGE_FILE = Path("chat_messages.json")
UPLOAD_DIR = Path("chat_uploads")

ROOM_COLUMNS = ["방이름", "생성일시", "참여자"]
MESSAGE_COLUMNS = ["일시", "방이름", "작성자", "메시지", "첨부파일명", "첨부경로", "첨부타입"]

IMAGE_TYPES = ["png", "jpg", "jpeg", "gif", "webp"]


# =========================
# JSON / 파일 유틸
# =========================
def init_json_files():
    UPLOAD_DIR.mkdir(exist_ok=True)

    if not ROOM_FILE.exists():
        save_json(ROOM_FILE, [])

    if not MESSAGE_FILE.exists():
        save_json(MESSAGE_FILE, [])


def load_json(path):
    if not path.exists():
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            return data

        return []
    except Exception:
        return []


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def normalize_rows(rows, columns):
    normalized = []

    for row in rows:
        if not isinstance(row, dict):
            continue

        new_row = {}
        for col in columns:
            new_row[col] = str(row.get(col, "") or "")

        normalized.append(new_row)

    return normalized


def load_rooms():
    init_json_files()
    rooms = load_json(ROOM_FILE)
    return normalize_rows(rooms, ROOM_COLUMNS)


def save_rooms(rooms):
    rooms = normalize_rows(rooms, ROOM_COLUMNS)
    save_json(ROOM_FILE, rooms)


def load_messages():
    init_json_files()
    messages = load_json(MESSAGE_FILE)
    return normalize_rows(messages, MESSAGE_COLUMNS)


def save_messages(messages):
    messages = normalize_rows(messages, MESSAGE_COLUMNS)
    save_json(MESSAGE_FILE, messages)


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def safe_text(value):
    return html.escape(str(value))


def split_participants(text):
    if not text:
        return []
    return [x.strip() for x in str(text).split(",") if x.strip()]


def join_participants(names):
    unique_names = []
    for name in names:
        name = str(name).strip()
        if name and name not in unique_names:
            unique_names.append(name)
    return ", ".join(unique_names)


def is_admin():
    return st.session_state.user_name.strip() == ADMIN_NAME


def sanitize_filename(filename):
    filename = filename.strip()
    filename = re.sub(r'[\\/:*?"<>|]', "_", filename)
    return filename


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


def make_json_download(data):
    return json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")


# =========================
# 방 관련 기능
# =========================
def create_room(room_name):
    rooms = load_rooms()

    if any(room["방이름"] == room_name for room in rooms):
        return False, "이미 같은 이름의 방이 있어요."

    new_room = {
        "방이름": room_name,
        "생성일시": now_text(),
        "참여자": ""
    }

    rooms.append(new_room)
    save_rooms(rooms)

    return True, "방을 만들었어요."


def delete_room(room_name):
    rooms = load_rooms()
    messages = load_messages()

    # 해당 방의 이미지 파일 삭제
    room_messages = [msg for msg in messages if msg["방이름"] == room_name]

    for row in room_messages:
        attach_path = str(row.get("첨부경로", "")).strip()
        if attach_path:
            path = Path(attach_path)
            if path.exists():
                try:
                    path.unlink()
                except Exception:
                    pass

    rooms = [room for room in rooms if room["방이름"] != room_name]
    messages = [msg for msg in messages if msg["방이름"] != room_name]

    save_rooms(rooms)
    save_messages(messages)


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
            participants = split_participants(room["참여자"])
            participants = [name for name in participants if name != user_name]
            room["참여자"] = join_participants(participants)
            break

    save_rooms(rooms)


def kick_user(room_name, target_user):
    leave_room(room_name, target_user)


def get_room_participants(room_name):
    rooms = load_rooms()

    for room in rooms:
        if room["방이름"] == room_name:
            return split_participants(room["참여자"])

    return []


# =========================
# 메시지 관련 기능
# =========================
def add_message(room_name, user_name, message, uploaded_file=None):
    messages = load_messages()

    attach_name, attach_path, attach_type = save_uploaded_image(uploaded_file)

    new_message = {
        "일시": now_text(),
        "방이름": room_name,
        "작성자": user_name,
        "메시지": message,
        "첨부파일명": attach_name,
        "첨부경로": attach_path,
        "첨부타입": attach_type
    }

    messages.append(new_message)
    save_messages(messages)


# =========================
# Streamlit 화면 설정
# =========================
st.set_page_config(
    page_title="프로젝트 대화 로그방",
    page_icon="💬",
    layout="wide"
)

st.markdown("""
<style>
html, body, [class*="css"] {
    font-family: "Gungsuh", "궁서", serif !important;
    font-weight: 700 !important;
}

.stButton button {
    font-weight: 900 !important;
    border-radius: 14px !important;
    padding: 0.55rem 0.8rem !important;
}

.chat-wrap {
    padding: 8px 4px 14px 4px;
}

.chat-left {
    max-width: 75%;
    border: 1px solid #ddd;
    border-radius: 16px;
    padding: 10px 14px;
    margin: 8px 0;
    background-color: transparent;
}

.chat-right {
    max-width: 75%;
    border: 1px solid #999;
    border-radius: 16px;
    padding: 10px 14px;
    margin: 8px 0 8px auto;
    background-color: transparent;
}

.chat-meta {
    font-size: 12px;
    color: #666;
    margin-bottom: 5px;
}

.chat-message {
    font-size: 16px;
    color: inherit;
    white-space: pre-wrap;
    line-height: 1.45;
}

.room-title {
    font-size: 26px;
    font-weight: 900;
    margin-bottom: 4px;
}

.small-guide {
    font-size: 13px;
    color: #777;
    margin-bottom: 12px;
}

.admin-box {
    border: 1px solid #999;
    border-radius: 14px;
    padding: 10px;
    margin-top: 8px;
    margin-bottom: 8px;
}

div[data-testid="stTextInput"] input {
    font-weight: 800 !important;
}
</style>
""", unsafe_allow_html=True)


# =========================
# 초기화
# =========================
init_json_files()

if "selected_room" not in st.session_state:
    st.session_state.selected_room = ""

if "user_name" not in st.session_state:
    st.session_state.user_name = ""

if "pending_user_name" not in st.session_state:
    st.session_state.pending_user_name = ""

if "message_box_key" not in st.session_state:
    st.session_state.message_box_key = 0

if "image_box_key" not in st.session_state:
    st.session_state.image_box_key = 0


st.title("💬 프로젝트 대화 로그방")
st.caption("내부망에서 프로젝트별 대화 로그를 남기기 위한 Streamlit + JSON 기반 프로토타입")


# =========================
# 자동 갱신 대화 로그
# =========================
@st.fragment(run_every="2s")
def render_chat_log(selected_room, search_keyword, current_user):
    messages = load_messages()
    room_messages = [msg for msg in messages if msg["방이름"] == selected_room]

    if search_keyword.strip():
        keyword = search_keyword.strip().lower()

        room_messages = [
            msg for msg in room_messages
            if keyword in msg.get("메시지", "").lower()
            or keyword in msg.get("작성자", "").lower()
            or keyword in msg.get("첨부파일명", "").lower()
        ]

    st.subheader("📜 대화 로그")
    st.caption("약 2초마다 자동으로 새 메시지를 확인해요.")

    if not room_messages:
        st.info("아직 대화가 없어.")
        return

    room_messages = sorted(room_messages, key=lambda x: x.get("일시", ""))

    with st.container(height=500):
        for row in room_messages:
            writer = str(row.get("작성자", ""))
            css_class = "chat-right" if writer == current_user else "chat-left"

            message_text = str(row.get("메시지", "")).strip()
            attach_name = str(row.get("첨부파일명", "")).strip()
            attach_path = str(row.get("첨부경로", "")).strip()

            st.markdown(f"""
            <div class="{css_class}">
                <div class="chat-meta">🕒 {safe_text(row.get("일시", ""))} · 👤 {safe_text(writer)}</div>
                <div class="chat-message">{safe_text(message_text)}</div>
            </div>
            """, unsafe_allow_html=True)

            if attach_path and Path(attach_path).exists():
                st.image(attach_path, caption=f"🖼️ {attach_name}", width=320)
            elif attach_name:
                st.warning(f"첨부 이미지 파일을 찾을 수 없어: {attach_name}")


# =========================
# 레이아웃
# =========================
left, right = st.columns([1, 2])


# =========================
# 왼쪽: 내 정보 / 방 목록
# =========================
with left:
    st.subheader("🙋 내 정보")

    name_col, button_col = st.columns([3, 1])

    with name_col:
        st.text_input(
            "내 이름 입력",
            placeholder="본인 이름",
            key="pending_user_name"
        )

    with button_col:
        st.write("")
        if st.button("이름 설정 완료", use_container_width=True):
            entered_name = st.session_state.pending_user_name.strip()

            if not entered_name:
                st.warning("이름을 입력해줘.")
            else:
                st.session_state.user_name = entered_name
                st.success(f"{entered_name} 님으로 설정됐어요.")
                st.rerun()

    if st.session_state.user_name:
        st.info(f"현재 이름: {st.session_state.user_name}")

    if is_admin():
        st.success("🛡️ 관리자 모드입니다.")

    st.divider()

    st.subheader("🌱 새 방 만들기")

    new_room_name = st.text_input(
        "새 방 이름 입력",
        placeholder="예: AI Agent QA 프로젝트"
    )

    if st.button("🌱 방 만들기", use_container_width=True):
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

    st.subheader("🚪 대화방 목록")

    rooms = load_rooms()
    room_names = [room["방이름"] for room in rooms]

    if len(room_names) == 0:
        st.info("아직 만들어진 방이 없어.")
    else:
        for room_name in room_names:
            label = f"✅ {room_name}" if st.session_state.selected_room == room_name else f"🚪 {room_name}"

            if st.button(label, key=f"room_{room_name}", use_container_width=True):
                st.session_state.selected_room = room_name
                st.rerun()


# =========================
# 오른쪽: 현재 방
# =========================
with right:
    selected_room = st.session_state.selected_room

    if not selected_room:
        st.info("왼쪽에서 방을 만들거나 선택해줘.")
    else:
        st.markdown(
            f'<div class="room-title">🚪 현재 방: {safe_text(selected_room)}</div>',
            unsafe_allow_html=True
        )

        st.markdown(
            '<div class="small-guide">메시지를 입력하고 Enter를 누르거나, 오른쪽 🚀 버튼을 누르면 바로 저장돼요.</div>',
            unsafe_allow_html=True
        )

        # =========================
        # 현재 방 참여자
        # =========================
        participants = get_room_participants(selected_room)

        with st.expander("👥 현재 방 참여자 보기", expanded=True):
            if participants:
                for person in participants:
                    col_name, col_kick = st.columns([5, 1])

                    with col_name:
                        if person == ADMIN_NAME:
                            st.write(f"🛡️ {person}")
                        else:
                            st.write(f"👤 {person}")

                    with col_kick:
                        if is_admin() and person != ADMIN_NAME:
                            if st.button("강퇴", key=f"kick_{selected_room}_{person}"):
                                kick_user(selected_room, person)
                                st.warning(f"{person} 님을 현재 방에서 내보냈어요.")
                                st.rerun()
            else:
                st.caption("아직 참여자가 없어.")

            col_join, col_leave = st.columns(2)

            with col_join:
                if st.button("🙌 이 방 참여하기", use_container_width=True):
                    if not st.session_state.user_name:
                        st.warning("먼저 내 이름을 설정해줘.")
                    else:
                        join_room(selected_room, st.session_state.user_name)
                        st.success("현재 방에 참여했어요.")
                        st.rerun()

            with col_leave:
                if st.button("👋 이 방 나가기", use_container_width=True):
                    if not st.session_state.user_name:
                        st.warning("먼저 내 이름을 설정해줘.")
                    else:
                        leave_room(selected_room, st.session_state.user_name)
                        st.success("현재 방에서 나갔어요.")
                        st.rerun()

        # =========================
        # 관리자 기능
        # =========================
        if is_admin():
            st.markdown('<div class="admin-box">🛡️ 관리자 기능</div>', unsafe_allow_html=True)

            delete_confirm = st.checkbox(
                f"'{selected_room}' 방 삭제 확인",
                key=f"delete_confirm_{selected_room}"
            )

            if st.button("🗑️ 현재 방 삭제", use_container_width=True):
                if not delete_confirm:
                    st.warning("방을 삭제하려면 먼저 삭제 확인 체크를 해줘.")
                else:
                    delete_room(selected_room)
                    st.session_state.selected_room = ""
                    st.success("방과 해당 방의 대화 로그를 삭제했어요.")
                    st.rerun()

        st.divider()

        # =========================
        # 검색
        # =========================
        search_keyword = st.text_input(
            "🔎 대화 검색",
            placeholder="메시지, 작성자, 첨부파일명 검색"
        )

        # =========================
        # 로그 다운로드
        # =========================
        all_messages = load_messages()
        room_messages = [msg for msg in all_messages if msg["방이름"] == selected_room]

        json_data = make_json_download(room_messages)

        st.download_button(
            label="📥 현재 방 로그 JSON 다운로드",
            data=json_data,
            file_name=f"{selected_room}_대화로그.json",
            mime="application/json",
            use_container_width=True
        )

        st.divider()

        # =========================
        # 대화 로그
        # =========================
        render_chat_log(
            selected_room=selected_room,
            search_keyword=search_keyword,
            current_user=st.session_state.user_name
        )

        st.divider()

        # =========================
        # 메시지 작성
        # =========================
        st.subheader("✍️ 메시지 작성")

        with st.form("message_form", clear_on_submit=False):
            col_input, col_image, col_send = st.columns([7, 2, 1])

            with col_input:
                message_key = f"message_input_{st.session_state.message_box_key}"
                message = st.text_input(
                    "메시지 입력",
                    placeholder="메시지를 입력하고 Enter를 눌러줘.",
                    label_visibility="collapsed",
                    key=message_key
                )

            with col_image:
                image_key = f"image_input_{st.session_state.image_box_key}"
                uploaded_image = st.file_uploader(
                    "이미지",
                    type=IMAGE_TYPES,
                    label_visibility="collapsed",
                    key=image_key
                )

            with col_send:
                submitted = st.form_submit_button("🚀", use_container_width=True)

            if submitted:
                if not st.session_state.user_name:
                    st.warning("먼저 왼쪽에서 내 이름을 설정해줘.")
                elif not message.strip() and uploaded_image is None:
                    st.warning("메시지나 이미지를 입력해줘.")
                else:
                    join_room(selected_room, st.session_state.user_name)
                    add_message(
                        room_name=selected_room,
                        user_name=st.session_state.user_name,
                        message=message.strip(),
                        uploaded_file=uploaded_image
                    )

                    st.session_state.message_box_key += 1
                    st.session_state.image_box_key += 1

                    st.rerun()
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse

from vnag.utility import get_folder_path

from .database import SqliteFeedbackDatabase

# 配置变量
STORAGE_DIR: Path = get_folder_path("feedbacks")

DB_PATH: Path = STORAGE_DIR / "feedback.db"

# 初始化数据库
db: SqliteFeedbackDatabase = SqliteFeedbackDatabase(str(DB_PATH))

app: FastAPI = FastAPI(title="vnag feedback server")


@app.post("/api/feedback")  # type: ignore[misc]
async def upload_feedback(
    session_file: UploadFile = File(...),
    profile_file: UploadFile = File(...),
    user_id: str = Form(...),
    session_id: str = Form(...),
    session_name: str = Form(...),
    profile_name: str = Form(...),
    profile_hash: str = Form(...),
    model: str = Form(...),
    rating: str = Form(...),
    comment: str = Form(""),
) -> JSONResponse:
    """接收反馈上传"""
    user_dir: Path = STORAGE_DIR / user_id

    # 保存session文件
    now: datetime = datetime.now()
    session_dir: Path = (
        user_dir
        / "sessions"
        / f"{now.year:04d}"
        / f"{now.month:02d}"
        / f"{now.day:02d}"
    )
    session_dir.mkdir(parents=True, exist_ok=True)

    session_path: Path = session_dir / f"{session_id}.json"
    session_content: bytes = await session_file.read()
    session_path.write_bytes(session_content)

    # 保存profile文件（去重）
    profiles_dir: Path = user_dir / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)

    profile_filename: str
    if profile_file.filename:
        profile_filename = profile_file.filename
    else:
        profile_filename = ""

    profile_path: Path = profiles_dir / profile_filename
    if not profile_path.exists():
        profile_content: bytes = await profile_file.read()
        profile_path.write_bytes(profile_content)

    # 生成相对路径
    session_rel_path: str = str(session_path.relative_to(STORAGE_DIR))

    # 保存到数据库
    success: bool = db.save_feedback(
        user_id=user_id,
        session_id=session_id,
        session_name=session_name,
        profile_name=profile_name,
        profile_hash=profile_hash,
        model=model,
        rating=rating,
        comment=comment,
        session_file_path=session_rel_path,
    )

    if success:
        result: JSONResponse = JSONResponse({"status": "ok"})
        return result

    error_result: JSONResponse
    error_result = JSONResponse({"status": "error"}, status_code=500)
    return error_result


@app.get("/api/feedbacks")  # type: ignore[misc]
async def load_feedbacks(
    user_id: str | None = None,
    rating: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
) -> dict:
    """加载反馈"""
    feedbacks: list[dict] = db.load_feedbacks(user_id, rating, start_time, end_time)
    result: dict = {"feedbacks": feedbacks}
    return result

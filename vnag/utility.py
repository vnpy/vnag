import json
import sys

from pathlib import Path
import pypdf


def _get_agent_dir(temp_name: str) -> tuple[Path, Path]:
    """获取运行时目录"""
    cwd: Path = Path.cwd()
    temp_path: Path = cwd.joinpath(temp_name)

    # 如果.vnag目录存在，则使用它作为运行时目录
    if temp_path.exists():
        return cwd, temp_path

    # 否则使用系统家目录
    home_path: Path = Path.home()
    temp_path = home_path.joinpath(temp_name)

    # 如果.vnag目录不存在，则创建它
    if not temp_path.exists():
        temp_path.mkdir()

    return home_path, temp_path


AGENT_DIR, TEMP_DIR = _get_agent_dir(".vnag")
sys.path.append(str(AGENT_DIR))


def get_file_path(filename: str) -> Path:
    """获取临时文件路径"""
    return TEMP_DIR.joinpath(filename)


def get_folder_path(folder_name: str) -> Path:
    """获取临时文件夹路径"""
    folder_path: Path = TEMP_DIR.joinpath(folder_name)
    if not folder_path.exists():
        folder_path.mkdir()
    return folder_path


def load_json(filename: str) -> dict:
    """加载JSON文件"""
    filepath: Path = get_file_path(filename)

    if filepath.exists():
        with open(filepath, encoding="UTF-8") as f:
            data: dict = json.load(f)
        return data
    else:
        return {}


def save_json(filename: str, data: dict | list) -> None:
    """保存JSON文件"""
    filepath: Path = get_file_path(filename)

    with open(filepath, mode="w+", encoding="UTF-8") as f:
        json.dump(
            data,
            f,
            indent=4,
            ensure_ascii=False
        )


def read_text_file(path: str | Path) -> str:
    """读取文本文件，使用 UTF-8 编码。"""
    p: Path = Path(path)
    text: str = p.read_text(encoding="utf-8")
    return text


def read_pdf_file(path: str | Path) -> str:
    """读取 PDF 文件为纯文本。"""
    p: Path = Path(path)
    text: str = ""
    with open(p, "rb") as file:
        reader: pypdf.PdfReader = pypdf.PdfReader(file)
        for page in reader.pages:
            page_text: str | None = page.extract_text()
            if page_text is None:
                page_text = ""
            text += page_text + "\n"
    return text


def write_text_file(path: str | Path, content: str) -> None:
    """写入文本文件，使用 UTF-8 编码（覆盖写）。"""
    p: Path = Path(path)
    p.write_text(content, encoding="utf-8")

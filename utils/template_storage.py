import hashlib
from pathlib import Path
from typing import Optional, Tuple

TEMPLATES_DIR = Path("templates")
TEMPLATES_DIR.mkdir(exist_ok=True)


def compute_content_hash(content: str) -> str:
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]


def supports_image_feature(html_content: str) -> bool:
    return 'image-container' in html_content or 'couple-image' in html_content


def save_template(content: str) -> Tuple[str, bool]:
    content_hash = compute_content_hash(content)
    file_path = TEMPLATES_DIR / f"{content_hash}.html"
    
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    
    is_new = not file_path.exists()
    
    if is_new:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    return content_hash, is_new


def get_template_path(content_hash: str) -> Optional[Path]:
    file_path = TEMPLATES_DIR / f"{content_hash}.html"
    if file_path.exists():
        return file_path
    return None


def read_template(content_hash: str) -> Optional[str]:
    file_path = TEMPLATES_DIR / f"{content_hash}.html"
    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    return None


def delete_template(content_hash: str) -> bool:
    file_path = TEMPLATES_DIR / f"{content_hash}.html"
    if file_path.exists():
        file_path.unlink()
        return True
    return False


def template_exists(content_hash: str) -> bool:
    file_path = TEMPLATES_DIR / f"{content_hash}.html"
    return file_path.exists()

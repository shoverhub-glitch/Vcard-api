import base64
import hashlib
from pathlib import Path
from typing import Optional

PLAYWRIGHT_AVAILABLE = True

try:
    from playwright.async_api import async_playwright
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

THUMBNAILS_DIR = Path("thumbnails")
THUMBNAILS_DIR.mkdir(exist_ok=True)

SAMPLE_DATA = {
    "person1Name": "Sarah",
    "person2Name": "James",
    "person1Family": "Daughter of Mr. & Mrs. Anderson",
    "person2Family": "Son of Mr. & Mrs. Williams",
    "brideName": "Sarah",
    "groomName": "James",
    "brideFamily": "Daughter of Mr. & Mrs. Anderson",
    "groomFamily": "Son of Mr. & Mrs. Williams",
    "eventDate": "Saturday, December 15th, 2026",
    "eventTime": "5:00 PM onwards",
    "venue": "Grand Ballroom, Hilton Hotel",
    "message": "We request the honor of your presence as we unite in marriage.",
    "imageUrl": "https://images.pexels.com/photos/265856/pexels-photo-265856.jpeg",
    "imageDisplay": "block",
}


def compute_content_hash(content: str) -> str:
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]


def replace_placeholders(html: str) -> str:
    for key, value in SAMPLE_DATA.items():
        placeholder = f"{{{{{key}}}}}"
        html = html.replace(placeholder, value)
    return html


async def generate_thumbnail(html_content: str, content_hash: str) -> Optional[str]:
    if not PLAYWRIGHT_AVAILABLE:
        return None
    
    thumbnail_filename = f"{content_hash}.png"
    thumbnail_path = THUMBNAILS_DIR / thumbnail_filename
    
    THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)
    
    if thumbnail_path.exists():
        return f"/thumbnails/{thumbnail_filename}"
    
    rendered_html = replace_placeholders(html_content)
    
    html_with_wrapper = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                width: 600px;
                min-height: 800px;
                display: flex;
                justify-content: center;
                align-items: center;
            }}
        </style>
    </head>
    <body>
        {rendered_html}
    </body>
    </html>
    """
    
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 600, "height": 800})
        
        await page.set_content(html_with_wrapper, wait_until="networkidle")
        await page.wait_for_timeout(500)
        
        await page.screenshot(path=str(thumbnail_path), type="png", full_page=False)
        await browser.close()
    
    return f"/thumbnails/{thumbnail_filename}"


async def generate_thumbnail_base64(html_content: str) -> Optional[str]:
    if not PLAYWRIGHT_AVAILABLE:
        return None
    
    rendered_html = replace_placeholders(html_content)
    
    html_with_wrapper = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                width: 600px;
                min-height: 800px;
                display: flex;
                justify-content: center;
                align-items: center;
            }}
        </style>
    </head>
    <body>
        {rendered_html}
    </body>
    </html>
    """
    
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 600, "height": 800})
        
        await page.set_content(html_with_wrapper, wait_until="networkidle")
        await page.wait_for_timeout(500)
        
        screenshot = await page.screenshot(type="png", full_page=False)
        await browser.close()
        
        return base64.b64encode(screenshot).decode("utf-8")
    
    return None


def get_thumbnail_path(content_hash: str) -> Optional[str]:
    thumbnail_path = THUMBNAILS_DIR / f"{content_hash}.png"
    if thumbnail_path.exists():
        return f"/thumbnails/{content_hash}.png"
    return None


def thumbnail_exists(content_hash: str) -> bool:
    thumbnail_path = THUMBNAILS_DIR / f"{content_hash}.png"
    return thumbnail_path.exists()


def delete_thumbnail(content_hash: str) -> bool:
    thumbnail_path = THUMBNAILS_DIR / f"{content_hash}.png"
    if thumbnail_path.exists():
        thumbnail_path.unlink()
        return True
    return False

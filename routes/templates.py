from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form, Query, Depends
from fastapi.responses import FileResponse
from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from pathlib import Path

from database import get_database
from schemas.schemas import TemplateCreate, TemplateUpdate, TemplateResponse, EventType
from utils.thumbnail_service import generate_thumbnail, get_thumbnail_path, thumbnail_exists
from utils.template_storage import save_template, read_template, template_exists, compute_content_hash
from utils.cache import get_cached, set_cached, invalidate_cache
from .auth import get_admin_user
from schemas.schemas_auth import UserInDB

router = APIRouter(prefix="/api/templates", tags=["templates"])

COLLECTION_NAME = "templates"
THUMBNAILS_DIR = Path("thumbnails")
TEMPLATES_DIR = Path("templates")


def validate_object_id(id: str) -> ObjectId:
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid ID format")
    return ObjectId(id)


def template_helper(template) -> dict:
    content_hash = template.get("content_hash", "")
    
    thumbnail_url = ""
    if content_hash:
        thumb_path = get_thumbnail_path(content_hash)
        if thumb_path:
            thumbnail_url = thumb_path
    
    html_path = None
    if content_hash:
        html_path = TEMPLATES_DIR / f"{content_hash}.html"
    
    return {
        "id": str(template["_id"]),
        "name": template["name"],
        "description": template.get("description", ""),
        "thumbnail": thumbnail_url,
        "category": template.get("category", ""),
        "tags": template.get("tags", []),
        "event_type": template.get("event_type", EventType.OTHER),
        "is_premium": template.get("is_premium", False),
        "price": template.get("price"),
        "supports_image": template.get("supports_image", True),
        "content_hash": content_hash,
        "has_html": html_path.exists() if html_path else False,
        "created_at": template.get("created_at", datetime.utcnow()),
        "updated_at": template.get("updated_at", datetime.utcnow()),
    }


@router.get("/", response_model=List[TemplateResponse])
async def get_all_templates(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    event_type: Optional[EventType] = Query(None, description="Filter by event type"),
    is_premium: Optional[bool] = Query(None, description="Filter by premium status"),
    search: Optional[str] = Query(None, description="Search in name/description"),
):
    cache_key = f"templates:list:{page}:{limit}:{event_type}:{is_premium}:{search}"
    cached = get_cached(cache_key)
    if cached:
        return cached
    
    db = get_database()
    
    query = {}
    
    if event_type:
        query["event_type"] = event_type.value if hasattr(event_type, 'value') else event_type
    
    if is_premium is not None:
        query["is_premium"] = is_premium
    
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}}
        ]
    
    skip = (page - 1) * limit
    
    total = await db[COLLECTION_NAME].count_documents(query)
    templates = []
    
    cursor = db[COLLECTION_NAME].find(query).skip(skip).limit(limit).sort("created_at", -1)
    async for template in cursor:
        templates.append(template_helper(template))
    
    set_cached(cache_key, templates, ttl=1800)
    return templates


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(template_id: str):
    validate_object_id(template_id)
    
    cache_key = f"templates:detail:{template_id}"
    cached = get_cached(cache_key)
    if cached:
        return cached
    
    db = get_database()
    template = await db[COLLECTION_NAME].find_one({"_id": ObjectId(template_id)})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    result = template_helper(template)
    set_cached(cache_key, result, ttl=3600)
    return result


@router.get("/{template_id}/html")
async def get_template_html(template_id: str):
    validate_object_id(template_id)
    db = get_database()
    template = await db[COLLECTION_NAME].find_one({"_id": ObjectId(template_id)})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    content_hash = template.get("content_hash", "")
    if not content_hash:
        raise HTTPException(status_code=404, detail="Template HTML not found")
    
    html_content = read_template(content_hash)
    if not html_content:
        raise HTTPException(status_code=404, detail="Template HTML file not found")
    
    return {"html_content": html_content}


@router.get("/{template_id}/thumbnail")
async def get_template_thumbnail(template_id: str):
    validate_object_id(template_id)
    db = get_database()
    template = await db[COLLECTION_NAME].find_one({"_id": ObjectId(template_id)})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    content_hash = template.get("content_hash", "")
    if not content_hash:
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    
    thumbnail_path = THUMBNAILS_DIR / f"{content_hash}.png"
    if not thumbnail_path.exists():
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    return FileResponse(thumbnail_path)


@router.post("/", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(template: TemplateCreate):
    db = get_database()
    now = datetime.utcnow()
    template_dict = template.model_dump()
    
    html_content = template_dict.get("html_content", "")
    content_hash = ""
    
    if html_content:
        content_hash, is_new = save_template(html_content)
        template_dict["content_hash"] = content_hash
        
        if is_new:
            await generate_thumbnail(html_content, content_hash)
    
    template_dict["created_at"] = now
    template_dict["updated_at"] = now
    template_dict.pop("html_content", None)
    
    result = await db[COLLECTION_NAME].insert_one(template_dict)
    created_template = await db[COLLECTION_NAME].find_one({"_id": result.inserted_id})
    
    from utils.cache import clear_all_cache
    
    return template_helper(created_template)


@router.post("/upload", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def upload_template(
    current_user: UserInDB = Depends(get_admin_user),
    name: str = Form(...),
    description: str = Form(""),
    category: str = Form("modern"),
    tags: str = Form(""),
    event_type: str = Form("other"),
    is_premium: bool = Form(False),
    price: Optional[float] = Form(None),
    html_file: UploadFile = File(...),
):
    if not html_file.filename or not html_file.filename.lower().endswith(".html"):
        raise HTTPException(status_code=400, detail="Only HTML files are allowed")
    
    content = await html_file.read()
    html_content = content.decode("utf-8")
    
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    
    content_hash, is_new = save_template(html_content)
    
    if is_new:
        await generate_thumbnail(html_content, content_hash)
    
    db = get_database()
    now = datetime.utcnow()
    template_dict = {
        "name": name,
        "description": description,
        "category": category,
        "tags": tag_list,
        "event_type": event_type,
        "is_premium": is_premium,
        "price": price,
        "content_hash": content_hash,
        "created_at": now,
        "updated_at": now,
    }
    
    result = await db[COLLECTION_NAME].insert_one(template_dict)
    
    created_template = await db[COLLECTION_NAME].find_one({"_id": ObjectId(str(result.inserted_id))})
    return template_helper(created_template)


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(template_id: str, template: TemplateUpdate, current_user: UserInDB = Depends(get_admin_user)):
    validate_object_id(template_id)
    db = get_database()
    update_data = {k: v for k, v in template.model_dump().items() if v is not None}
    
    if "html_content" in update_data and update_data["html_content"]:
        html_content = update_data["html_content"]
        content_hash = compute_content_hash(html_content)
        
        if not template_exists(content_hash):
            save_template(html_content)
            await generate_thumbnail(html_content, content_hash)
        
        update_data["content_hash"] = content_hash
        del update_data["html_content"]
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    update_data["updated_at"] = datetime.utcnow()
    
    await db[COLLECTION_NAME].update_one(
        {"_id": ObjectId(template_id)}, {"$set": update_data}
    )
    updated_template = await db[COLLECTION_NAME].find_one({"_id": ObjectId(template_id)})
    if not updated_template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    from utils.cache import clear_all_cache
    return template_helper(updated_template)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(template_id: str, current_user: UserInDB = Depends(get_admin_user)):
    validate_object_id(template_id)
    db = get_database()
    
    template = await db[COLLECTION_NAME].find_one({"_id": ObjectId(template_id)})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    result = await db[COLLECTION_NAME].delete_one({"_id": ObjectId(template_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    
    from utils.cache import clear_all_cache
    
    content_hash = template.get("content_hash", "")
    if content_hash:
        count = await db[COLLECTION_NAME].count_documents({"content_hash": content_hash})
        if count == 0:
            from utils.thumbnail_service import delete_thumbnail as del_thumb
            del_thumb(content_hash)
            from utils.template_storage import delete_template as del_tmpl
            del_tmpl(content_hash)


@router.post("/{template_id}/regenerate-thumbnail", response_model=TemplateResponse)
async def regenerate_thumbnail(template_id: str, current_user: UserInDB = Depends(get_admin_user)):
    validate_object_id(template_id)
    db = get_database()
    template = await db[COLLECTION_NAME].find_one({"_id": ObjectId(template_id)})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    content_hash = template.get("content_hash", "")
    if content_hash:
        html_content = read_template(content_hash)
        if html_content:
            await generate_thumbnail(html_content, content_hash)
    
    updated_template = await db[COLLECTION_NAME].find_one({"_id": ObjectId(template_id)})
    return template_helper(updated_template)

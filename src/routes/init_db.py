from fastapi import APIRouter, HTTPException
from dataApp import init_db

router = APIRouter(prefix="/init-db", tags=["Database"])


@router.post("")
def init_database():
    try:
        init_db()
        return {"message": "Database initialized successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

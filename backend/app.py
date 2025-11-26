# app.py
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import configparser
from datetime import datetime

from query_data import (
    query_info_last_updated,
    query_all_ranking_players,
    get_current_season
)

# 读取配置文件
config = configparser.ConfigParser()
config.read('config.txt')

# 获取允许的域名列表
allowed_origins = []
if config.has_section('cors') and config.has_option('cors', 'allowed_origins'):
    origins_str = config.get('cors', 'allowed_origins')
    if origins_str.strip():
        allowed_origins = [origin.strip() for origin in origins_str.split(',')]

app = FastAPI(title="Snooker Calendar API", version="1.0.0")

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="ics_calendars"), name="static")

class PlayerFilter(BaseModel):
    nationality: Optional[str] = None
    min_ranking: Optional[int] = None
    max_ranking: Optional[int] = None
    has_upcoming_matches: Optional[bool] = None

@app.get("/api/players")
def get_players(
    page: int = 1, 
    limit: int = 50,
    search: Optional[str] = None
):
    """获取玩家列表"""
    try:
        players = query_all_ranking_players(page=page, limit=limit, search=search)
        return players
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/calendar/{player_id}")
def download_player_calendar(player_id: int):
    """下载指定玩家的ICS日历文件"""
    try:
        # 检查文件是否存在
        filepath = f"ics_calendars/{player_id}.ics"
        if not os.path.exists(filepath):
            # 如果不存在，实时生成
            from player_matches_to_ics import generate_player_calendar
            ics_content = generate_player_calendar(player_id, get_current_season())
            
            if not ics_content:
                raise HTTPException(status_code=404, detail="No matches found")
            
            # 保存文件
            os.makedirs(f"ics_calendars", exist_ok=True)
            with open(filepath, 'wb') as f:
                f.write(ics_content)
        
        return FileResponse(
            filepath, 
            media_type='text/calendar',
            filename=f"player_{player_id}.ics"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/info/lastupdated")
def get_last_updated_info():
    """获取最后更新时间"""
    try:
        last_updated = query_info_last_updated()
        return last_updated
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
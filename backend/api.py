"""API endpoints"""
import logging
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from agents.graph import agent_graph
from db.database import get_session
from db.models import Measurement, Forecast, Alert, Analysis
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)
router = APIRouter()


class AgentResponse(BaseModel):
    """Response from agent execution"""
    status: str
    message: str
    data: dict


class MeasurementOut(BaseModel):
    """Measurement response schema"""
    id: int
    location_name: str
    latitude: float
    longitude: float
    timestamp: datetime
    pm25: Optional[float] = None
    pm10: Optional[float] = None
    no2: Optional[float] = None
    o3: Optional[float] = None
    co: Optional[float] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    
    class Config:
        from_attributes = True


class ForecastOut(BaseModel):
    """Forecast response schema"""
    id: int
    location_name: str
    forecast_time: datetime
    predicted_pm25: Optional[float]
    predicted_aqi: Optional[int]
    
    class Config:
        from_attributes = True


class AlertOut(BaseModel):
    """Alert response schema"""
    id: int
    location_name: str
    severity: str
    message: str
    created_at: datetime
    
    class Config:
        from_attributes = True


@router.post("/run-agent/{task_type}", response_model=AgentResponse)
async def run_agent(task_type: str):
    """Execute agent task"""
    valid_tasks = ["collect_data", "analyze", "forecast", "check_alerts"]
    
    if task_type not in valid_tasks:
        raise HTTPException(400, f"Invalid task. Must be one of: {valid_tasks}")
    
    try:
        logger.info(f"Running agent task: {task_type}")
        
        # Запускаем граф
        result = await agent_graph.ainvoke({
            "messages": [HumanMessage(content=f"Execute {task_type}")],
            "task_type": task_type,
            "next_agent": "",
            "data": {}
        })
        
        # Извлекаем результат
        last_message = result["messages"][-1] if result["messages"] else None
        response_message = last_message.content if last_message else "Task completed"
        
        return AgentResponse(
            status="success",
            message=response_message,
            data=result.get("data", {})
        )
    
    except Exception as e:
        logger.error(f"Agent execution error: {e}", exc_info=True)
        raise HTTPException(500, f"Agent execution failed: {str(e)}")


@router.get("/data/measurements", response_model=List[MeasurementOut])
async def get_measurements(
    hours: int = 24,
    location: Optional[str] = None,
    session: AsyncSession = Depends(get_session)
):
    """Get recent measurements"""
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    query = select(Measurement).where(Measurement.timestamp >= cutoff_time)
    
    if location:
        query = query.where(Measurement.location_name == location)
    
    query = query.order_by(Measurement.timestamp.desc()).limit(1000)
    result = await session.execute(query)
    measurements = result.scalars().all()
    
    return measurements


@router.get("/data/forecasts", response_model=List[ForecastOut])
async def get_forecasts(
    session: AsyncSession = Depends(get_session)
):
    """Get recent forecasts"""
    query = select(Forecast).order_by(Forecast.created_at.desc()).limit(100)
    result = await session.execute(query)
    forecasts = result.scalars().all()
    
    return forecasts


@router.get("/data/alerts", response_model=List[AlertOut])
async def get_alerts(
    active_only: bool = True,
    session: AsyncSession = Depends(get_session)
):
    """Get alerts"""
    query = select(Alert)
    
    if active_only:
        query = query.where(Alert.is_active == True)
    
    query = query.order_by(Alert.created_at.desc()).limit(100)
    result = await session.execute(query)
    alerts = result.scalars().all()
    
    return alerts


@router.get("/data/analyses")
async def get_analyses(
    hours: int = 168,
    session: AsyncSession = Depends(get_session)
):
    """Get recent analyses"""
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    query = select(Analysis).where(
        Analysis.created_at >= cutoff
    ).order_by(Analysis.created_at.desc()).limit(100)
    
    result = await session.execute(query)
    analyses = result.scalars().all()
    
    return [
        {
            "id": a.id,
            "location_name": a.location_name,
            "pm25_trend": a.pm25_trend,
            "pm25_avg": a.pm25_avg,
            "anomalies_count": a.anomalies_count,
            "summary": a.summary,
            "detailed_analysis": a.detailed_analysis,
            "created_at": a.created_at.isoformat()
        }
        for a in analyses
    ]


@router.get("/data/current")
async def get_current_status(session: AsyncSession = Depends(get_session)):
    """Get current status summary"""
    # Latest measurements
    cutoff = datetime.utcnow() - timedelta(hours=1)
    measurements_query = select(Measurement).where(
        Measurement.timestamp >= cutoff
    ).order_by(Measurement.timestamp.desc())
    
    measurements_result = await session.execute(measurements_query)
    recent_measurements = measurements_result.scalars().all()
    
    # Active alerts
    alerts_query = select(Alert).where(Alert.is_active == True)
    alerts_result = await session.execute(alerts_query)
    active_alerts = alerts_result.scalars().all()
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "measurements_count": len(recent_measurements),
        "active_alerts_count": len(active_alerts),
        "locations": list(set(m.location_name for m in recent_measurements))
    }

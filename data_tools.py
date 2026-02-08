"""Инструменты для агентов - взаимодействие с API и БД"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import httpx
import numpy as np
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Measurement, Forecast, Alert
from config import settings

logger = logging.getLogger(__name__)


async def fetch_air_quality_data(lat: float, lon: float) -> Dict:
    """Получение данных о качестве воздуха через Open-Meteo API"""
    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,ozone",
        "timezone": "Europe/Moscow",
        "forecast_days": 1
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Error fetching air quality: {e}")
        return {}


async def fetch_weather_data(lat: float, lon: float) -> Dict:
    """Получение метеоданных через Open-Meteo API"""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,relative_humidity_2m,windspeed_10m",
        "timezone": "Europe/Moscow",
        "forecast_days": 1
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Error fetching weather: {e}")
        return {}


async def save_measurements(session: AsyncSession, data: List[Dict]) -> int:
    """Сохранение измерений в БД"""
    
    saved_count = 0
    for item in data:
        try:
            # Проверяем, не существует ли уже такая запись
            existing = await session.execute(
                select(Measurement).where(
                    Measurement.location_name == item["location_name"],
                    Measurement.timestamp == item["timestamp"]
                )
            )
            
            if existing.scalars().first():
                logger.debug(f"Skipping duplicate: {item['location_name']} at {item['timestamp']}")
                continue
            
            measurement = Measurement(**item)
            session.add(measurement)
            saved_count += 1
        except Exception as e:
            logger.error(f"Error saving measurement: {e}")
    
    await session.commit()
    return saved_count



async def get_recent_measurements(
    session: AsyncSession,
    hours: int = 168,
    location_name: Optional[str] = None
) -> List[Measurement]:
    """Получение последних измерений из БД"""
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    query = select(Measurement).where(Measurement.timestamp >= cutoff_time)
    
    if location_name:
        query = query.where(Measurement.location_name == location_name)
    
    query = query.order_by(Measurement.timestamp.desc())
    result = await session.execute(query)
    return result.scalars().all()


async def save_forecast(session: AsyncSession, forecast_data: Dict) -> Forecast:
    """Сохранение прогноза в БД"""
    forecast = Forecast(**forecast_data)
    session.add(forecast)
    await session.commit()
    await session.refresh(forecast)
    return forecast


async def save_alert(session: AsyncSession, alert_data: Dict) -> Alert:
    """Сохранение алерта в БД"""
    alert = Alert(**alert_data)
    session.add(alert)
    await session.commit()
    await session.refresh(alert)
    return alert


async def get_active_alerts(session: AsyncSession) -> List[Alert]:
    """Получение активных алертов"""
    query = select(Alert).where(
        and_(
            Alert.is_active == True,
            Alert.created_at >= datetime.utcnow() - timedelta(hours=24)
        )
    ).order_by(Alert.created_at.desc())
    
    result = await session.execute(query)
    return result.scalars().all()


def calculate_aqi(pm25: float) -> int:
    """Упрощенный расчет AQI на основе PM2.5"""
    if pm25 <= 12.0:
        return int((50 / 12.0) * pm25)
    elif pm25 <= 35.4:
        return int(50 + ((100 - 50) / (35.4 - 12.1)) * (pm25 - 12.1))
    elif pm25 <= 55.4:
        return int(100 + ((150 - 100) / (55.4 - 35.5)) * (pm25 - 35.5))
    elif pm25 <= 150.4:
        return int(150 + ((200 - 150) / (150.4 - 55.5)) * (pm25 - 55.5))
    elif pm25 <= 250.4:
        return int(200 + ((300 - 200) / (250.4 - 150.5)) * (pm25 - 150.5))
    else:
        return int(300 + ((500 - 300) / (500.4 - 250.5)) * (pm25 - 250.5))


def analyze_trend(values: List[float]) -> str:
    """Анализ тренда временного ряда"""
    if len(values) < 2:
        return "insufficient_data"
    
    values_array = np.array(values)
    slope = np.polyfit(range(len(values)), values_array, 1)[0]
    
    if slope > 0.5:
        return "increasing"
    elif slope < -0.5:
        return "decreasing"
    else:
        return "stable"


def detect_anomalies(values: List[float], threshold: float = 2.0) -> List[int]:
    """Обнаружение аномалий методом z-score"""
    if len(values) < 3:
        return []
    
    values_array = np.array(values)
    mean = np.mean(values_array)
    std = np.std(values_array)
    
    if std == 0:
        return []
    
    z_scores = np.abs((values_array - mean) / std)
    anomaly_indices = np.where(z_scores > threshold)[0].tolist()
    
    return anomaly_indices

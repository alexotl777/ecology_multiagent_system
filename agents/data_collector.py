"""Агент сбора данных с Open-Meteo API"""
import logging
from datetime import datetime
from typing import Dict, List
from langchain_core.messages import AIMessage

from config import settings
from data_tools import (
    fetch_air_quality_data,
    fetch_weather_data,
    save_measurements,
)
from db.database import get_session

logger = logging.getLogger(__name__)


class DataCollectorAgent:
    """Агент для сбора данных о качестве воздуха и погоде"""
    
    def __init__(self):
        self.name = "DataCollectorAgent"
    
    async def execute(self, state: Dict) -> Dict:
        """Выполнение сбора данных"""
        logger.info(f"{self.name}: Starting data collection")
        
        collected_data = []
        
        # Собираем данные для каждой точки мониторинга
        for location in settings.MONITORING_LOCATIONS:
            try:
                # Качество воздуха
                air_data = await fetch_air_quality_data(
                    location["lat"],
                    location["lon"]
                )
                
                # Погода
                weather_data = await fetch_weather_data(
                    location["lat"],
                    location["lon"]
                )
                
                # Комбинируем данные
                if air_data.get("hourly") and weather_data.get("hourly"):
                    hourly_air = air_data["hourly"]
                    hourly_weather = weather_data["hourly"]
                    
                    # ✅ ИСПРАВЛЕНИЕ: Берем последние 24 часа (все доступные данные)
                    num_points = min(len(hourly_air["time"]), 24)
                    
                    for i in range(-num_points, 0):  # От -24 до -1
                        try:
                            measurement = {
                                "location_name": location["name"],
                                "latitude": location["lat"],
                                "longitude": location["lon"],
                                "timestamp": datetime.fromisoformat(
                                    hourly_air["time"][i].replace("Z", "+00:00")
                                ),
                                "pm25": hourly_air.get("pm2_5", [None])[i],
                                "pm10": hourly_air.get("pm10", [None])[i],
                                "no2": hourly_air.get("nitrogen_dioxide", [None])[i],
                                "o3": hourly_air.get("ozone", [None])[i],
                                "co": hourly_air.get("carbon_monoxide", [None])[i],
                                "temperature": hourly_weather.get("temperature_2m", [None])[i],
                                "humidity": hourly_weather.get("relative_humidity_2m", [None])[i],
                            }
                            collected_data.append(measurement)
                        except Exception as e:
                            logger.error(f"Error processing hour {i}: {e}")
                            continue
                    
                    logger.info(f"Collected {num_points} hours of data for {location['name']}")
            
            except Exception as e:
                logger.error(f"Error collecting data for {location['name']}: {e}")
        
        # Сохраняем в БД
        saved_count = 0
        if collected_data:
            async for session in get_session():
                saved_count = await save_measurements(session, collected_data)
        
        message = AIMessage(
            content=f"✅ Collected {saved_count} measurements from {len(settings.MONITORING_LOCATIONS)} locations (last 24 hours)"
        )
        
        return {
            "messages": state["messages"] + [message],
            "data": {"collected": saved_count, "measurements": collected_data}
        }

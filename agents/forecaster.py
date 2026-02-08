"""Агент прогнозирования качества воздуха"""
import logging
from datetime import datetime, timedelta
from typing import Dict
import numpy as np
from langchain_core.messages import AIMessage
from sklearn.linear_model import LinearRegression

from config import settings
from data_tools import get_recent_measurements, save_forecast, calculate_aqi
from db.database import get_session

logger = logging.getLogger(__name__)


class ForecasterAgent:
    """Агент для прогнозирования на 24 часа"""
    
    def __init__(self):
        self.name = "ForecasterAgent"
    
    async def execute(self, state: Dict) -> Dict:
        """Выполнение прогнозирования"""
        logger.info(f"{self.name}: Starting forecast")
        
        forecasts = []
        
        # Получаем данные за последние 48 часов
        async for session in get_session():
            measurements = await get_recent_measurements(session, hours=48)
        
        if len(measurements) < 10:
            message = AIMessage(content="⚠️ Insufficient data for forecasting")
            return {"messages": state["messages"] + [message], "data": {}}
        
        # Группируем по локациям
        locations_data = {}
        for m in measurements:
            if m.location_name not in locations_data:
                locations_data[m.location_name] = {
                    "timestamps": [],
                    "pm25": [],
                    "lat": m.latitude,
                    "lon": m.longitude
                }
            locations_data[m.location_name]["timestamps"].append(m.timestamp)
            locations_data[m.location_name]["pm25"].append(m.pm25 or 0)
        
        # Прогнозируем для каждой локации
        for location, data in locations_data.items():
            if len(data["pm25"]) < 5:
                continue
            
            try:
                # Простой линейный прогноз
                X = np.array(range(len(data["pm25"]))).reshape(-1, 1)
                y = np.array(data["pm25"])
                
                model = LinearRegression()
                model.fit(X, y)
                
                # Прогноз на 24 часа вперед
                future_steps = 24
                future_X = np.array(range(len(data["pm25"]), len(data["pm25"]) + future_steps)).reshape(-1, 1)
                predictions = model.predict(future_X)
                
                # Ограничиваем прогноз разумными значениями
                predictions = np.clip(predictions, 0, 500)
                
                # Сохраняем прогноз
                forecast_time = datetime.utcnow() + timedelta(hours=24)
                predicted_pm25 = float(predictions[-1])
                predicted_aqi = calculate_aqi(predicted_pm25)
                
                forecast_data = {
                    "location_name": location,
                    "latitude": data["lat"],
                    "longitude": data["lon"],
                    "forecast_time": forecast_time,
                    "predicted_pm25": predicted_pm25,
                    "predicted_pm10": predicted_pm25 * 1.5,  # Упрощенная оценка
                    "predicted_aqi": predicted_aqi,
                    "confidence": 0.75,
                }
                
                async for session in get_session():
                    await save_forecast(session, forecast_data)
                
                forecasts.append({
                    "location": location,
                    "pm25": predicted_pm25,
                    "aqi": predicted_aqi
                })
            
            except Exception as e:
                logger.error(f"Forecast error for {location}: {e}")
        
        forecast_text = "\n".join([
            f"📍 {f['location']}: PM2.5={f['pm25']:.1f}, AQI={f['aqi']}"
            for f in forecasts
        ])
        
        message = AIMessage(
            content=f"🔮 Прогноз на 24 часа:\n\n{forecast_text}"
        )
        
        return {
            "messages": state["messages"] + [message],
            "data": {"forecasts": forecasts}
        }

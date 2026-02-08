"""Агент генерации алертов при превышении нормативов"""
import logging
from datetime import datetime
from typing import Dict
from langchain_core.messages import AIMessage

from config import settings
from data_tools import get_recent_measurements, save_alert, calculate_aqi
from db.database import get_session

logger = logging.getLogger(__name__)


class AlertAgentWorker:
    """Агент для генерации предупреждений"""
    
    def __init__(self):
        self.name = "AlertAgent"
    
    async def execute(self, state: Dict) -> Dict:
        """Проверка превышений и генерация алертов"""
        logger.info(f"{self.name}: Checking for alerts")
        
        alerts_created = []
        
        # Получаем последние измерения
        async for session in get_session():
            measurements = await get_recent_measurements(session, hours=1)
        
        if not measurements:
            message = AIMessage(content="⚠️ No recent data to check")
            return {"messages": state["messages"] + [message], "data": {}}
        
        # Проверяем каждое измерение
        for m in measurements:
            if not m.pm25:
                continue
            
            aqi = calculate_aqi(m.pm25)
            
            # Генерируем алерт если AQI > 100 (Unhealthy for Sensitive Groups)
            if aqi > settings.AQI_THRESHOLDS["moderate"]:
                severity = "warning"
                if aqi > settings.AQI_THRESHOLDS["unhealthy"]:
                    severity = "danger"
                
                alert_data = {
                    "location_name": m.location_name,
                    "latitude": m.latitude,
                    "longitude": m.longitude,
                    "alert_type": "high_aqi",
                    "severity": severity,
                    "message": f"Высокий уровень загрязнения! PM2.5={m.pm25:.1f}, AQI={aqi}",
                    "value": m.pm25,
                    "threshold": settings.AQI_THRESHOLDS["moderate"],
                    "is_active": True,
                }
                
                async for session in get_session():
                    alert = await save_alert(session, alert_data)
                    alerts_created.append({
                        "location": alert.location_name,
                        "severity": alert.severity,
                        "message": alert.message
                    })
        
        if alerts_created:
            alert_text = "\n".join([
                f"🚨 {a['severity'].upper()}: {a['location']} - {a['message']}"
                for a in alerts_created
            ])
            message = AIMessage(content=f"Создано алертов: {len(alerts_created)}\n\n{alert_text}")
        else:
            message = AIMessage(content="✅ Все показатели в норме, алертов нет")
        
        return {
            "messages": state["messages"] + [message],
            "data": {"alerts": alerts_created}
        }

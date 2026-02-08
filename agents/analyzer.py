"""Агент анализа экологических данных"""
import logging
from typing import Dict
from langchain_core.messages import AIMessage
from langchain_groq import ChatGroq

from config import settings
from data_tools import get_recent_measurements, analyze_trend, detect_anomalies
from db.database import get_session

logger = logging.getLogger(__name__)


class AnalyzerAgent:
    """Агент для анализа трендов и аномалий"""
    
    def __init__(self):
        self.name = "AnalyzerAgent"
        self.llm = ChatGroq(
            temperature=0.3,
            model_name=settings.GROQ_MODEL,
            groq_api_key=settings.GROQ_API_KEY
        )
    
    async def execute(self, state: Dict) -> Dict:
        """Выполнение анализа данных"""
        logger.info(f"{self.name}: Starting analysis")
        
        analysis_results = []
        
        # Получаем данные за последнюю неделю
        async for session in get_session():
            measurements = await get_recent_measurements(session, hours=168)
        
        if not measurements:
            message = AIMessage(content="⚠️ No data available for analysis")
            return {"messages": state["messages"] + [message], "data": {}}
        
        # Группируем по локациям
        locations_data = {}
        for m in measurements:
            if m.location_name not in locations_data:
                locations_data[m.location_name] = {"pm25": [], "pm10": [], "no2": []}
            
            if m.pm25:
                locations_data[m.location_name]["pm25"].append(m.pm25)
            if m.pm10:
                locations_data[m.location_name]["pm10"].append(m.pm10)
            if m.no2:
                locations_data[m.location_name]["no2"].append(m.no2)
        
        # Анализируем тренды и аномалии
        for location, data in locations_data.items():
            pm25_trend = analyze_trend(data["pm25"]) if data["pm25"] else "no_data"
            pm25_anomalies = detect_anomalies(data["pm25"]) if len(data["pm25"]) > 3 else []
            
            analysis_results.append({
                "location": location,
                "pm25_trend": pm25_trend,
                "pm25_anomalies_count": len(pm25_anomalies),
                "avg_pm25": sum(data["pm25"]) / len(data["pm25"]) if data["pm25"] else 0,
            })
        
        # Генерируем текстовый отчет с помощью LLM
        analysis_text = "\n".join([
            f"📍 {r['location']}: PM2.5 тренд={r['pm25_trend']}, "
            f"среднее={r['avg_pm25']:.1f}, аномалий={r['pm25_anomalies_count']}"
            for r in analysis_results
        ])
        
        prompt = f"""Проанализируй экологические данные за неделю:

{analysis_text}

Дай краткую оценку ситуации (2-3 предложения) на русском языке."""
        
        try:
            response = await self.llm.ainvoke(prompt)
            summary = response.content
        except Exception as e:
            logger.error(f"LLM analysis error: {e}")
            summary = "Анализ выполнен, данные собраны."
        
        message = AIMessage(content=f"📊 Анализ завершен:\n\n{summary}")
        
        return {
            "messages": state["messages"] + [message],
            "data": {"analysis": analysis_results}
        }

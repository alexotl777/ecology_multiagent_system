"""Агент анализа экологических данных"""
import logging
from typing import Dict
from datetime import datetime, timedelta
from langchain_core.messages import AIMessage
from langchain_groq import ChatGroq

from config import settings
from data_tools import get_recent_measurements, analyze_trend, detect_anomalies
from db.database import get_session
from db.models import Analysis

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
        period_end = datetime.utcnow()
        period_start = period_end - timedelta(hours=168)
        
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
                locations_data[m.location_name] = {"pm25": [], "pm10": [], "no2": [], "temp": []}
            
            if m.pm25:
                locations_data[m.location_name]["pm25"].append(m.pm25)
            if m.pm10:
                locations_data[m.location_name]["pm10"].append(m.pm10)
            if m.no2:
                locations_data[m.location_name]["no2"].append(m.no2)
            if m.temperature:
                locations_data[m.location_name]["temp"].append(m.temperature)
        
        # Анализируем тренды и аномалии
        for location, data in locations_data.items():
            pm25_trend = analyze_trend(data["pm25"]) if data["pm25"] else "no_data"
            pm25_anomalies = detect_anomalies(data["pm25"]) if len(data["pm25"]) > 3 else []
            avg_pm25 = sum(data["pm25"]) / len(data["pm25"]) if data["pm25"] else 0
            max_pm25 = max(data["pm25"]) if data["pm25"] else 0
            min_pm25 = min(data["pm25"]) if data["pm25"] else 0
            avg_temp = sum(data["temp"]) / len(data["temp"]) if data["temp"] else 0
            
            analysis_results.append({
                "location": location,
                "pm25_trend": pm25_trend,
                "pm25_anomalies_count": len(pm25_anomalies),
                "avg_pm25": avg_pm25,
                "max_pm25": max_pm25,
                "min_pm25": min_pm25,
                "avg_temp": avg_temp,
            })
        
        # Генерируем детальный отчет для каждой локации
        analysis_text = "\n".join([
            f"📍 {r['location']}:\n"
            f"   - Тренд: {r['pm25_trend']}\n"
            f"   - PM2.5: среднее={r['avg_pm25']:.1f}, мин={r['min_pm25']:.1f}, макс={r['max_pm25']:.1f}\n"
            f"   - Аномалий: {r['pm25_anomalies_count']}\n"
            f"   - Средняя температура: {r['avg_temp']:.1f}°C"
            for r in analysis_results[:10]  # Берем первые 10 для контекста
        ])
        
        # Расширенный промпт для LLM
        detailed_prompt = f"""Ты - эксперт-эколог, анализирующий качество воздуха в крупных городах России за последнюю неделю.

ДАННЫЕ ЗА НЕДЕЛЮ:
{analysis_text}

СПРАВКА:
- PM2.5 норма: до 25 μg/m³ (ВОЗ), 35 μg/m³ (допустимо)
- AQI: 0-50 хорошо, 51-100 умеренно, 101+ вредно

Составь ПОДРОБНЫЙ анализ (4-6 абзацев) на русском языке:

1. **Общая оценка обстановки**: какие города в лучшем/худшем состоянии, есть ли критичные превышения?

2. **Тренды и динамика**: какие города показывают ухудшение (increasing), улучшение (decreasing) или стабильность?

3. **Аномалии и выбросы**: где зафиксированы резкие скачки загрязнения, возможные причины (погода, сезонность)?

4. **Риски для здоровья**: для каких групп населения текущая обстановка опасна, какие симптомы возможны?

5. **Рекомендации**: что советуешь жителям (ограничить прогулки, использовать маски, проветривание) и властям (контроль выбросов, транспорт)?

Пиши понятным языком, но профессионально. Используй emoji для наглядности."""

        try:
            # Краткое резюме
            summary_prompt = f"На основе данных: {analysis_text}\n\nНапиши КРАТКОЕ резюме (1-2 предложения) общей экологической обстановки."
            summary_response = await self.llm.ainvoke(summary_prompt)
            summary = summary_response.content
            
            # Детальный анализ
            detailed_response = await self.llm.ainvoke(detailed_prompt)
            detailed_analysis = detailed_response.content
            
        except Exception as e:
            logger.error(f"LLM analysis error: {e}")
            summary = "Анализ выполнен, данные собраны за неделю."
            detailed_analysis = "Детальный анализ временно недоступен."
        
        # Сохраняем результаты в БД
        async for session in get_session():
            for result in analysis_results:
                try:
                    analysis = Analysis(
                        analysis_type="weekly_trend",
                        location_name=result["location"],
                        pm25_trend=result["pm25_trend"],
                        pm25_avg=result["avg_pm25"],
                        anomalies_count=result["pm25_anomalies_count"],
                        summary=summary,
                        detailed_analysis=detailed_analysis,
                        period_start=period_start,
                        period_end=period_end
                    )
                    session.add(analysis)
                except Exception as e:
                    logger.error(f"Error saving analysis: {e}")
            
            await session.commit()
        
        message = AIMessage(content=f"📊 Анализ завершен:\n\n{summary}\n\nПодробности доступны на вкладке 'Анализ'")
        
        return {
            "messages": state["messages"] + [message],
            "data": {"analysis": analysis_results, "summary": summary, "detailed_analysis": detailed_analysis}
        }

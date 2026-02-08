"""LangGraph мультиагентный граф с supervisor"""
import logging
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor
import operator

from agents.data_collector import DataCollectorAgent
from agents.analyzer import AnalyzerAgent
from agents.forecaster import ForecasterAgent
from agents.alert_agent import AlertAgentWorker
from config import settings

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """Состояние мультиагентной системы"""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    next_agent: str
    task_type: str
    data: dict


def create_supervisor_chain():
    """Создание supervisor агента для роутинга задач"""
    llm = ChatGroq(
        temperature=0,
        model_name=settings.GROQ_MODEL,
        groq_api_key=settings.GROQ_API_KEY
    )
    
    system_prompt = """Вы - координатор мультиагентной системы экологического мониторинга.
    
Доступные агенты:
- data_collector: Сбор данных с API (температура, влажность, PM2.5, PM10, NO2, O3, CO)
- analyzer: Анализ данных (тренды, аномалии, корреляции)
- forecaster: Прогнозирование на 24 часа
- alert_agent: Генерация предупреждений при превышении нормативов

Определите, какой агент должен выполнить задачу. Отвечайте ТОЛЬКО названием агента.

Примеры:
- "собрать данные" -> data_collector
- "проанализировать тренды" -> analyzer
- "прогноз на завтра" -> forecaster
- "проверить превышения" -> alert_agent
"""
    
    def supervisor_node(state: AgentState) -> AgentState:
        """Supervisor узел для определения следующего агента"""
        messages = state["messages"]
        task_type = state.get("task_type", "unknown")
        
        # Простой роутинг на основе типа задачи
        routing_map = {
            "collect_data": "data_collector",
            "analyze": "analyzer",
            "forecast": "forecaster",
            "check_alerts": "alert_agent",
        }
        
        next_agent = routing_map.get(task_type, "data_collector")
        
        logger.info(f"Supervisor routing to: {next_agent}")
        return {"next_agent": next_agent, "messages": messages, "data": state.get("data", {})}
    
    return supervisor_node


def create_agent_graph():
    """Создание LangGraph мультиагентного графа"""
    
    # Создаем агентов
    data_collector = DataCollectorAgent()
    analyzer = AnalyzerAgent()
    forecaster = ForecasterAgent()
    alert_agent = AlertAgentWorker()
    
    # Создаем граф
    workflow = StateGraph(AgentState)
    
    # Добавляем узлы
    workflow.add_node("supervisor", create_supervisor_chain())
    workflow.add_node("data_collector", data_collector.execute)
    workflow.add_node("analyzer", analyzer.execute)
    workflow.add_node("forecaster", forecaster.execute)
    workflow.add_node("alert_agent", alert_agent.execute)
    
    # Conditional routing от supervisor к агентам
    workflow.add_conditional_edges(
        "supervisor",
        lambda state: state["next_agent"],
        {
            "data_collector": "data_collector",
            "analyzer": "analyzer",
            "forecaster": "forecaster",
            "alert_agent": "alert_agent",
        }
    )
    
    # Все агенты возвращаются в END
    workflow.add_edge("data_collector", END)
    workflow.add_edge("analyzer", END)
    workflow.add_edge("forecaster", END)
    workflow.add_edge("alert_agent", END)
    
    # Устанавливаем точку входа
    workflow.set_entry_point("supervisor")
    
    return workflow.compile()


# Глобальный инстанс графа
agent_graph = create_agent_graph()

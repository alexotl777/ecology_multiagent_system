import os
from typing import List, Dict, Any, ClassVar
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra='ignore'
    )
    
    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://ecomonitor:securepass123@localhost:5432/eco_monitoring"
    )
    
    # API Keys
    GROQ_API_KEY: str = Field(default="")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO")
    
    # GROQ Model
    GROQ_MODEL: str = Field(default="llama3-8b-8192")
    
    # ✅ Крупнейшие города России (ClassVar = не поле модели)
    MAJOR_CITIES: ClassVar[List[Dict[str, Any]]] = [
        {"name": "Москва", "lat": 55.7558, "lon": 37.6176},
        {"name": "Санкт-Петербург", "lat": 59.9311, "lon": 30.3609},
        {"name": "Новосибирск", "lat": 55.0084, "lon": 82.9357},
        {"name": "Екатеринбург", "lat": 56.8389, "lon": 60.6057},
        {"name": "Казань", "lat": 55.7887, "lon": 49.1221},
        {"name": "Нижний Новгород", "lat": 56.2965, "lon": 43.9361},
        {"name": "Челябинск", "lat": 55.1644, "lon": 61.4368},
        {"name": "Самара", "lat": 53.1959, "lon": 50.1002},
        {"name": "Уфа", "lat": 54.7388, "lon": 55.9721},
        {"name": "Ростов-на-Дону", "lat": 47.2357, "lon": 39.7015},
    ]
    
    # ✅ Генерируем точки мониторинга
    MONITORING_LOCATIONS: ClassVar[List[Dict[str, Any]]] = []
    
    # ✅ AQI пороги
    AQI_THRESHOLDS: ClassVar[Dict[str, int]] = {
        "good": 50,
        "moderate": 100,
        "unhealthy_sensitive": 150,
        "unhealthy": 200,
        "very_unhealthy": 300,
    }


# ✅ Генерируем точки после определения класса
for city in Settings.MAJOR_CITIES:
    Settings.MONITORING_LOCATIONS.extend([
        {"name": f"{city['name']} (Центр)", "lat": city["lat"], "lon": city["lon"]},
        {"name": f"{city['name']} (Север)", "lat": city["lat"] + 0.1, "lon": city["lon"]},
        {"name": f"{city['name']} (Юг)", "lat": city["lat"] - 0.1, "lon": city["lon"]},
    ])

# Создаем инстанс
settings = Settings()

print(f"🌍 Инициализировано {len(settings.MONITORING_LOCATIONS)} точек мониторинга в {len(settings.MAJOR_CITIES)} городах")

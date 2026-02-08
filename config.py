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
    GROQ_MODEL: str = Field(default="llama-3.3-70b-versatile")
    
    # ✅ Крупнейшие города России
    MAJOR_CITIES_RUSSIA: ClassVar[List[Dict[str, Any]]] = [
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
    
    # ✅ Крупнейшие города Индии
    MAJOR_CITIES_INDIA: ClassVar[List[Dict[str, Any]]] = [
        {"name": "Дели", "lat": 28.6139, "lon": 77.2090},
        {"name": "Мумбаи", "lat": 19.0760, "lon": 72.8777},
        {"name": "Калькутта", "lat": 22.5726, "lon": 88.3639},
        {"name": "Бангалор", "lat": 12.9716, "lon": 77.5946},
        {"name": "Ченнаи", "lat": 13.0827, "lon": 80.2707},
        {"name": "Хайдарабад", "lat": 17.3850, "lon": 78.4867},
        {"name": "Ахмадабад", "lat": 23.0225, "lon": 72.5714},
        {"name": "Пуна", "lat": 18.5204, "lon": 73.8567},
    ]
    
    # ✅ Объединяем все города
    MAJOR_CITIES: ClassVar[List[Dict[str, Any]]] = MAJOR_CITIES_RUSSIA + MAJOR_CITIES_INDIA
    
    # Генерируем точки мониторинга
    MONITORING_LOCATIONS: ClassVar[List[Dict[str, Any]]] = []
    
    # AQI пороги
    AQI_THRESHOLDS: ClassVar[Dict[str, int]] = {
        "good": 50,
        "moderate": 100,
        "unhealthy_sensitive": 150,
        "unhealthy": 200,
        "very_unhealthy": 300,
    }


# Генерируем точки после определения класса
for city in Settings.MAJOR_CITIES:
    Settings.MONITORING_LOCATIONS.extend([
        {"name": f"{city['name']} (Центр)", "lat": city["lat"], "lon": city["lon"]},
        {"name": f"{city['name']} (Север)", "lat": city["lat"] + 0.1, "lon": city["lon"]},
        {"name": f"{city['name']} (Юг)", "lat": city["lat"] - 0.1, "lon": city["lon"]},
    ])

# Создаем инстанс
settings = Settings()

print(f"🌍 Инициализировано {len(settings.MONITORING_LOCATIONS)} точек мониторинга")
print(f"   - Россия: {len(settings.MAJOR_CITIES_RUSSIA)} городов")
print(f"   - Индия: {len(settings.MAJOR_CITIES_INDIA)} городов")

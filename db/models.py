"""SQLAlchemy ORM модели"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, Index, UniqueConstraint
from db.database import Base


class Measurement(Base):
    """Измерения качества воздуха и погоды"""
    __tablename__ = "measurements"
    
    id = Column(Integer, primary_key=True, index=True)
    location_name = Column(String(100), nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # Загрязняющие вещества
    pm25 = Column(Float)  # PM2.5 (μg/m³)
    pm10 = Column(Float)  # PM10 (μg/m³)
    no2 = Column(Float)   # NO2 (μg/m³)
    o3 = Column(Float)    # O3 (μg/m³)
    co = Column(Float)    # CO (μg/m³)
    
    # Метео
    temperature = Column(Float)  # °C
    humidity = Column(Float)     # %
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_location_timestamp', 'location_name', 'timestamp'),
    )


class Forecast(Base):
    """Прогнозы качества воздуха"""
    __tablename__ = "forecasts"
    
    id = Column(Integer, primary_key=True, index=True)
    location_name = Column(String(100), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    forecast_time = Column(DateTime, nullable=False, index=True)
    
    predicted_pm25 = Column(Float)
    predicted_pm10 = Column(Float)
    predicted_aqi = Column(Integer)
    confidence = Column(Float)  # 0-1
    
    created_at = Column(DateTime, default=datetime.utcnow)


class Alert(Base):
    """Предупреждения о превышениях"""
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    location_name = Column(String(100), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    alert_type = Column(String(50), nullable=False)  # high_aqi, high_pm25, etc
    severity = Column(String(20), nullable=False)    # info, warning, danger
    message = Column(Text, nullable=False)
    
    value = Column(Float)       # Значение показателя
    threshold = Column(Float)   # Пороговое значение
    
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    resolved_at = Column(DateTime, nullable=True)


class Analysis(Base):
    """Результаты анализа данных"""
    __tablename__ = "analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    analysis_type = Column(String(50), nullable=False)
    location_name = Column(String(100), nullable=False, index=True)
    
    # Результаты
    pm25_trend = Column(String(20))
    pm25_avg = Column(Float)
    anomalies_count = Column(Integer, default=0)
    summary = Column(Text)  
    detailed_analysis = Column(Text) 
    
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        UniqueConstraint('location_name', 'created_at', name='unique_analysis'),
    )

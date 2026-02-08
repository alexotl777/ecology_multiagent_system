"""Streamlit Dashboard"""
import logging
from datetime import datetime, timedelta
import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_folium import folium_static
import folium
import httpx

from data_tools import calculate_aqi

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page config
st.set_page_config(
    page_title="🌍 Eco Monitor",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Title
st.title("🌍 Система экологического мониторинга")
st.markdown("*Мультиагентный анализ качества воздуха в реальном времени*")

# Backend URL
BACKEND_URL = "http://backend:8000"


# Helper functions
def get_aqi_color(aqi: int) -> str:
    """Цвет по AQI"""
    if aqi <= 50:
        return "green"
    elif aqi <= 100:
        return "yellow"
    elif aqi <= 150:
        return "orange"
    elif aqi <= 200:
        return "red"
    elif aqi <= 300:
        return "purple"
    else:
        return "darkred"


def fetch_measurements(hours=24):
    """Fetch measurements from backend API"""
    try:
        response = httpx.get(f"{BACKEND_URL}/api/data/measurements", params={"hours": hours}, timeout=30.0)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching measurements: {e}")
        return []


def fetch_alerts():
    """Fetch active alerts from backend API"""
    try:
        response = httpx.get(f"{BACKEND_URL}/api/data/alerts", params={"active_only": True}, timeout=30.0)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching alerts: {e}")
        return []


def fetch_forecasts():
    """Fetch forecasts from backend API"""
    try:
        response = httpx.get(f"{BACKEND_URL}/api/data/forecasts", timeout=30.0)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching forecasts: {e}")
        return []


def call_agent(task_type: str):
    """Call backend agent"""
    try:
        response = httpx.post(f"{BACKEND_URL}/api/run-agent/{task_type}", timeout=120.0)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Agent call error: {e}")
        return {"status": "error", "message": str(e)}


# Sidebar
with st.sidebar:
    st.header("⚙️ Управление")
    
    st.subheader("🤖 Агенты")
    
    if st.button("🔄 Обновить данные", use_container_width=True):
        with st.spinner("Собираем данные..."):
            result = call_agent("collect_data")
            if result.get("status") == "success":
                st.success(result.get("message", "Готово!"))
            else:
                st.error(result.get("message", "Ошибка"))
    
    if st.button("📊 Анализ", use_container_width=True):
        with st.spinner("Анализируем..."):
            result = call_agent("analyze")
            if result.get("status") == "success":
                st.info(result.get("message", "Готово!"))
    
    if st.button("🔮 Прогноз", use_container_width=True):
        with st.spinner("Прогнозируем..."):
            result = call_agent("forecast")
            if result.get("status") == "success":
                st.info(result.get("message", "Готово!"))
    
    if st.button("🚨 Проверка алертов", use_container_width=True):
        with st.spinner("Проверяем..."):
            result = call_agent("check_alerts")
            if result.get("status") == "success":
                st.info(result.get("message", "Готово!"))
    
    st.divider()
    
    st.subheader("📅 Период")
    time_range = st.selectbox(
        "Показать данные за:",
        ["1 час", "6 часов", "24 часа", "7 дней"],
        index=2
    )
    
    hours_map = {"1 час": 1, "6 часов": 6, "24 часа": 24, "7 дней": 168}
    selected_hours = hours_map[time_range]

# Main content
tab1, tab2, tab3, tab4 = st.tabs(["🗺️ Карта", "📈 Графики", "💬 Чат", "📋 Данные"])

# Tab 1: Map
with tab1:
    st.header("🗺️ Карта мониторинга")
    
    measurements = fetch_measurements(hours=1)
    
    if measurements:
        st.write(f"📊 Получено {len(measurements)} измерений")
        
        # Группируем по location_name
        unique_locations = {}
        for m in measurements:
            loc_name = m.get("location_name", "Unknown")
            if loc_name not in unique_locations:
                unique_locations[loc_name] = m
        
        st.write(f"📍 Уникальных локаций: **{len(unique_locations)}**")
        
        # Вычисляем центр карты
        lats = []
        lons = []
        for m in unique_locations.values():
            lat = m.get("latitude")
            lon = m.get("longitude")
            if lat is not None and lon is not None:
                lats.append(lat)
                lons.append(lon)
        
        if lats and lons:
            center_lat = sum(lats) / len(lats)
            center_lon = sum(lons) / len(lons)
            lat_range = max(lats) - min(lats)
            lon_range = max(lons) - min(lons)
            max_range = max(lat_range, lon_range)
            
            if max_range > 20:
                zoom = 4
            elif max_range > 10:
                zoom = 5
            elif max_range > 5:
                zoom = 6
            elif max_range > 2:
                zoom = 7
            else:
                zoom = 8
        else:
            center_lat, center_lon, zoom = 55.7558, 37.6176, 5
        
        # Создаем карту
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=zoom,
            tiles="OpenStreetMap"
        )
        
        # ✅ Добавляем маркеры с более мягкой проверкой
        points_added = 0
        skipped_no_coords = 0
        skipped_no_pm25 = 0
        
        for loc_name, measurement in unique_locations.items():
            lat = measurement.get("latitude")
            lon = measurement.get("longitude")
            pm25 = measurement.get("pm25")
            
            # Отладка
            if lat is None or lon is None:
                skipped_no_coords += 1
                continue
            
            if pm25 is None:
                skipped_no_pm25 += 1
                pm25 = 0  # ✅ Используем 0 вместо пропуска
            
            aqi = calculate_aqi(pm25) if pm25 > 0 else 0
            color = get_aqi_color(aqi)
            
            pm25_str = f"{pm25:.1f}" if pm25 else "N/A"

            folium.CircleMarker(
                location=[float(lat), float(lon)],
                radius=8,
                popup=folium.Popup(f"""
                    <div style='width: 200px'>
                        <b>{loc_name}</b><br>
                        <hr>
                        📍 {lat:.4f}, {lon:.4f}<br>
                        🌫️ PM2.5: <b>{pm25_str}</b> μg/m³<br>
                        📊 AQI: <b style='color:{color}'>{aqi}</b><br>
                        🕐 {measurement.get("timestamp", "N/A")}
                    </div>
                """, max_width=250),
                tooltip=f"{loc_name}: AQI {aqi}",
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.7,
                weight=2
            ).add_to(m)

            points_added += 1
        
        st.write(f"✅ На карте отображено: **{points_added}** точек")
        if skipped_no_coords > 0:
            st.warning(f"⚠️ Пропущено {skipped_no_coords} точек без координат")
        if skipped_no_pm25 > 0:
            st.info(f"ℹ️ {skipped_no_pm25} точек без PM2.5 (показаны как 0)")
        
        folium_static(m, width=1200, height=600)
        
        # Легенда
        st.markdown("""
        **Легенда AQI:**
        - 🟢 0-50: Хорошо
        - 🟡 51-100: Умеренно
        - 🟠 101-150: Вредно для чувствительных групп
        - 🔴 151-200: Вредно
        - 🟣 201-300: Очень вредно
        - ⚫ 300+: Опасно
        """)
    else:
        st.warning("⚠️ Нет данных для отображения. Нажмите '🔄 Обновить данные'")


# Tab 2: Charts
with tab2:
    st.header("Временные ряды")
    
    measurements = fetch_measurements(hours=selected_hours)
    
    if measurements:
        # Преобразуем в DataFrame
        df = pd.DataFrame(measurements)
        
        # График PM2.5
        if "pm25" in df.columns and "timestamp" in df.columns:
            fig_pm25 = px.line(
                df,
                x="timestamp",
                y="pm25",
                color="location_name",
                title="PM2.5 (μg/m³)",
                labels={"timestamp": "Время", "pm25": "PM2.5"}
            )
            st.plotly_chart(fig_pm25, use_container_width=True)
        
        # График температуры и влажности
        col1, col2 = st.columns(2)
        
        with col1:
            if "temperature" in df.columns:
                fig_temp = px.line(
                    df,
                    x="timestamp",
                    y="temperature",
                    color="location_name",
                    title="Температура (°C)"
                )
                st.plotly_chart(fig_temp, use_container_width=True)
        
        with col2:
            if "humidity" in df.columns:
                fig_hum = px.line(
                    df,
                    x="timestamp",
                    y="humidity",
                    color="location_name",
                    title="Влажность (%)"
                )
                st.plotly_chart(fig_hum, use_container_width=True)
    else:
        st.info("Загрузите данные для отображения графиков")

# Tab 3: Chat
with tab3:
    st.header("💬 Чат с агентами")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Display chat
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Задайте вопрос (например: 'Покажи прогноз на завтра')"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Думаю..."):
                # Простой роутинг запросов
                if "прогноз" in prompt.lower():
                    result = call_agent("forecast")
                elif "анализ" in prompt.lower() or "тренд" in prompt.lower():
                    result = call_agent("analyze")
                elif "данные" in prompt.lower() or "обнов" in prompt.lower():
                    result = call_agent("collect_data")
                elif "алерт" in prompt.lower() or "превышен" in prompt.lower():
                    result = call_agent("check_alerts")
                else:
                    result = {"status": "info", "message": "Попробуйте: 'прогноз', 'анализ', 'обновить данные', 'проверить алерты'"}
                
                response = result.get("message", "Готово!")
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

# Tab 4: Data tables
with tab4:
    st.header("📋 Таблицы данных")
    
    # Alerts
    st.subheader("🚨 Активные алерты")
    alerts = fetch_alerts()
    if alerts:
        alerts_df = pd.DataFrame(alerts)
        if not alerts_df.empty:
            display_cols = ["location_name", "severity", "message", "created_at"]
            available_cols = [col for col in display_cols if col in alerts_df.columns]
            st.dataframe(alerts_df[available_cols], use_container_width=True)
    else:
        st.success("✅ Нет активных алертов")
    
    # Forecasts
    st.subheader("🔮 Прогнозы")
    forecasts = fetch_forecasts()
    if forecasts:
        forecasts_df = pd.DataFrame(forecasts)
        if not forecasts_df.empty:
            display_cols = ["location_name", "forecast_time", "predicted_pm25", "predicted_aqi"]
            available_cols = [col for col in display_cols if col in forecasts_df.columns]
            st.dataframe(forecasts_df[available_cols], use_container_width=True)
    else:
        st.info("Нет прогнозов. Запустите агент 'Прогноз'")
    
    # Recent measurements
    st.subheader("📊 Последние измерения")
    measurements = fetch_measurements(hours=6)
    if measurements:
        measurements_df = pd.DataFrame(measurements[:50])
        if not measurements_df.empty:
            display_cols = ["location_name", "timestamp", "pm25", "pm10", "temperature"]
            available_cols = [col for col in display_cols if col in measurements_df.columns]
            st.dataframe(measurements_df[available_cols], use_container_width=True)
    else:
        st.warning("Нет данных")

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: gray;'>
    <small>Eco Monitor v1.0 | Powered by LangChain + LangGraph + GROQ | 2026</small>
</div>
""", unsafe_allow_html=True)

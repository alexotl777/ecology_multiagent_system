"""Streamlit Dashboard"""
import logging
from datetime import datetime, timedelta
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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


def fetch_measurements(hours=24, location=None):
    """Fetch measurements from backend API"""
    try:
        params = {"hours": hours}
        if location:
            params["location"] = location
        response = httpx.get(f"{BACKEND_URL}/api/data/measurements", params=params, timeout=30.0)
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


def extract_city_name(location_name: str) -> str:
    """Извлекает название города из полного имени локации"""
    return location_name.split(" (")[0] if " (" in location_name else location_name


# Sidebar
with st.sidebar:
    st.header("⚙️ Управление")
    
    st.subheader("🤖 Агенты")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Данные", use_container_width=True):
            with st.spinner("Собираем..."):
                result = call_agent("collect_data")
                if result.get("status") == "success":
                    st.success("✅ Готово!")
                    st.rerun()
                else:
                    st.error(result.get("message", "Ошибка"))
    
    with col2:
        if st.button("📊 Анализ", use_container_width=True):
            with st.spinner("Анализируем..."):
                result = call_agent("analyze")
                if result.get("status") == "success":
                    st.info("✅ Готово!")
                    st.rerun()
    
    col3, col4 = st.columns(2)
    with col3:
        if st.button("🔮 Прогноз", use_container_width=True):
            with st.spinner("Прогнозируем..."):
                result = call_agent("forecast")
                if result.get("status") == "success":
                    st.info("✅ Готово!")
    
    with col4:
        if st.button("🚨 Алерты", use_container_width=True):
            with st.spinner("Проверяем..."):
                result = call_agent("check_alerts")
                if result.get("status") == "success":
                    st.info("✅ Готово!")
    
    st.divider()
    
    # Фильтры
    st.subheader("🔍 Фильтры")
    
    # Получаем список городов
    all_measurements = fetch_measurements(hours=1)
    cities = ["Все города"] + sorted(list(set([extract_city_name(m.get("location_name", "")) for m in all_measurements])))
    
    selected_city = st.selectbox(
        "Город:",
        cities,
        index=0
    )
    
    time_range = st.selectbox(
        "Период:",
        ["1 час", "6 часов", "24 часа", "7 дней"],
        index=2
    )
    
    hours_map = {"1 час": 1, "6 часов": 6, "24 часа": 24, "7 дней": 168}
    selected_hours = hours_map[time_range]
    
    # Выбор показателей для графиков
    st.subheader("📈 Показатели")
    show_pm25 = st.checkbox("PM2.5", value=True)
    show_pm10 = st.checkbox("PM10", value=True)
    show_no2 = st.checkbox("NO2", value=False)
    show_o3 = st.checkbox("O3 (Озон)", value=False)
    show_co = st.checkbox("CO", value=False)
    show_temp = st.checkbox("Температура", value=True)
    show_aqi = st.checkbox("AQI", value=True)

# Получаем данные с учетом фильтра города
if selected_city != "Все города":
    measurements = [m for m in fetch_measurements(hours=selected_hours) if extract_city_name(m.get("location_name", "")) == selected_city]
else:
    measurements = fetch_measurements(hours=selected_hours)

# Main content
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🗺️ Карта", "📈 Графики", "📊 Статистика", "🔬 Анализ", "💬 Чат", "📋 Данные"])

# Tab 1: Map
with tab1:
    st.header("🗺️ Карта мониторинга")
    
    if selected_city != "Все города":
        st.info(f"🔍 Фильтр: **{selected_city}**")
    
    map_data = measurements if selected_city != "Все города" else fetch_measurements(hours=1)
    
    if map_data:
        # Группируем по location_name
        unique_locations = {}
        for m in map_data:
            loc_name = m.get("location_name", "Unknown")
            if loc_name not in unique_locations:
                unique_locations[loc_name] = m
        
        # Статистика
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📍 Локаций", len(unique_locations))
        with col2:
            avg_pm25 = sum([m.get("pm25", 0) for m in unique_locations.values() if m.get("pm25")]) / len(unique_locations) if unique_locations else 0
            st.metric("🌫️ Средний PM2.5", f"{avg_pm25:.1f} μg/m³")
        with col3:
            avg_aqi = sum([calculate_aqi(m.get("pm25", 0)) for m in unique_locations.values() if m.get("pm25")]) / len(unique_locations) if unique_locations else 0
            st.metric("📊 Средний AQI", f"{int(avg_aqi)}")
        with col4:
            cities_count = len(set([extract_city_name(loc) for loc in unique_locations.keys()]))
            st.metric("🏙️ Городов", cities_count)
        
        # Вычисляем центр карты
        lats = [m.get("latitude") for m in unique_locations.values() if m.get("latitude")]
        lons = [m.get("longitude") for m in unique_locations.values() if m.get("longitude")]
        
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
            elif max_range > 0.5:
                zoom = 9
            else:
                zoom = 10
        else:
            center_lat, center_lon, zoom = 55.7558, 37.6176, 5
        
        # Создаем карту
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=zoom,
            tiles="OpenStreetMap"
        )
        
        # Добавляем маркеры
        for loc_name, measurement in unique_locations.items():
            lat = measurement.get("latitude")
            lon = measurement.get("longitude")
            pm25 = measurement.get("pm25")
            
            if lat is None or lon is None:
                continue
            
            pm25_str = f"{pm25:.1f}" if pm25 else "N/A"
            pm10 = measurement.get("pm10")
            pm10_str = f"{pm10:.1f}" if pm10 else "N/A"
            no2 = measurement.get("no2")
            no2_str = f"{no2:.1f}" if no2 else "N/A"
            temp = measurement.get("temperature")
            temp_str = f"{temp:.1f}°C" if temp is not None else "N/A"
            
            aqi = calculate_aqi(pm25) if pm25 else 0
            color = get_aqi_color(aqi)
            
            folium.CircleMarker(
                location=[float(lat), float(lon)],
                radius=8,
                popup=folium.Popup(f"""
                    <div style='width: 240px; font-family: Arial'>
                        <h4 style='margin: 5px 0; color: #333'>{loc_name}</h4>
                        <hr style='margin: 8px 0; border: 0; border-top: 1px solid #ddd'>
                        <table style='width: 100%; font-size: 13px'>
                            <tr><td>📍 Координаты:</td><td><b>{lat:.4f}, {lon:.4f}</b></td></tr>
                            <tr><td>🌫️ PM2.5:</td><td><b>{pm25_str}</b> μg/m³</td></tr>
                            <tr><td>🌫️ PM10:</td><td><b>{pm10_str}</b> μg/m³</td></tr>
                            <tr><td>💨 NO2:</td><td><b>{no2_str}</b> μg/m³</td></tr>
                            <tr><td>🌡️ Температура:</td><td><b>{temp_str}</b></td></tr>
                            <tr><td>📊 AQI:</td><td><b style='color:{color}'>{aqi}</b></td></tr>
                        </table>
                    </div>
                """, max_width=280),
                tooltip=f"{loc_name}: AQI {aqi}",
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.7,
                weight=2
            ).add_to(m)
        
        folium_static(m, width=1200, height=600)
        
        # Легенда
        st.markdown("""
        **Легенда AQI:**
        🟢 0-50: Хорошо | 🟡 51-100: Умеренно | 🟠 101-150: Вредно для чувствительных | 🔴 151-200: Вредно | 🟣 201-300: Очень вредно | ⚫ 300+: Опасно
        """)
    else:
        st.warning("⚠️ Нет данных. Нажмите '🔄 Данные'")

# Tab 2: Charts
with tab2:
    st.header("📈 Временные ряды")
    
    if selected_city != "Все города":
        st.info(f"🔍 Фильтр: **{selected_city}**")
    
    if measurements and len(measurements) > 0:
        df = pd.DataFrame(measurements)
        df['city'] = df['location_name'].apply(extract_city_name)
        df['aqi'] = df['pm25'].apply(lambda x: calculate_aqi(x) if x else 0)
        
        st.write(f"📊 Загружено записей: **{len(df)}**")
        
        # PM2.5 и PM10
        if show_pm25 or show_pm10:
            fig = go.Figure()
            
            if show_pm25 and "pm25" in df.columns:
                for loc in df['location_name'].unique():
                    df_loc = df[df['location_name'] == loc].dropna(subset=["pm25"])
                    if not df_loc.empty:
                        fig.add_trace(go.Scatter(
                            x=df_loc["timestamp"],
                            y=df_loc["pm25"],
                            mode='lines+markers',
                            name=f"{loc} (PM2.5)",
                            line=dict(width=2)
                        ))
            
            if show_pm10 and "pm10" in df.columns:
                for loc in df['location_name'].unique():
                    df_loc = df[df['location_name'] == loc].dropna(subset=["pm10"])
                    if not df_loc.empty:
                        fig.add_trace(go.Scatter(
                            x=df_loc["timestamp"],
                            y=df_loc["pm10"],
                            mode='lines',
                            name=f"{loc} (PM10)",
                            line=dict(width=1, dash='dot')
                        ))
            
            fig.update_layout(
                title="PM2.5 и PM10 (μg/m³)",
                xaxis_title="Время",
                yaxis_title="Концентрация (μg/m³)",
                hovermode='x unified',
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # NO2, O3, CO
        if show_no2 or show_o3 or show_co:
            fig2 = go.Figure()
            
            if show_no2 and "no2" in df.columns:
                df_no2 = df.dropna(subset=["no2"])
                for loc in df_no2['location_name'].unique():
                    df_loc = df_no2[df_no2['location_name'] == loc]
                    fig2.add_trace(go.Scatter(x=df_loc["timestamp"], y=df_loc["no2"], mode='lines', name=f"{loc} (NO2)"))
            
            if show_o3 and "o3" in df.columns:
                df_o3 = df.dropna(subset=["o3"])
                for loc in df_o3['location_name'].unique():
                    df_loc = df_o3[df_o3['location_name'] == loc]
                    fig2.add_trace(go.Scatter(x=df_loc["timestamp"], y=df_loc["o3"], mode='lines', name=f"{loc} (O3)"))
            
            if show_co and "co" in df.columns:
                df_co = df.dropna(subset=["co"])
                for loc in df_co['location_name'].unique():
                    df_loc = df_co[df_co['location_name'] == loc]
                    fig2.add_trace(go.Scatter(x=df_loc["timestamp"], y=df_loc["co"], mode='lines', name=f"{loc} (CO)"))
            
            fig2.update_layout(title="Загрязняющие вещества (μg/m³)", xaxis_title="Время", yaxis_title="Концентрация", hovermode='x unified', height=400)
            st.plotly_chart(fig2, use_container_width=True)
        
        # Температура и AQI
        col1, col2 = st.columns(2)
        
        with col1:
            if show_temp and "temperature" in df.columns:
                df_temp = df.dropna(subset=["temperature"])
                fig_temp = px.line(df_temp, x="timestamp", y="temperature", color="location_name", title="Температура (°C)")
                st.plotly_chart(fig_temp, use_container_width=True)
        
        with col2:
            if show_aqi:
                fig_aqi = px.line(df, x="timestamp", y="aqi", color="location_name", title="AQI (Air Quality Index)")
                st.plotly_chart(fig_aqi, use_container_width=True)
    else:
        st.info("📥 Нет данных для графиков")

# Tab 3: Statistics
with tab3:
    st.header("📊 Статистика по городам")
    
    if measurements:
        df = pd.DataFrame(measurements)
        df['city'] = df['location_name'].apply(extract_city_name)
        df['aqi'] = df['pm25'].apply(lambda x: calculate_aqi(x) if x else 0)
        
        # Группируем по городам
        city_stats = df.groupby('city').agg({
            'pm25': ['mean', 'min', 'max', 'std'],
            'pm10': ['mean', 'min', 'max'],
            'temperature': 'mean',
            'aqi': 'mean'
        }).round(2)
        
        city_stats.columns = ['PM2.5 средн', 'PM2.5 мин', 'PM2.5 макс', 'PM2.5 σ', 'PM10 средн', 'PM10 мин', 'PM10 макс', 'Темп средн', 'AQI средн']
        
        st.dataframe(city_stats, use_container_width=True)
        
        # Диаграмма сравнения городов
        fig_compare = go.Figure()
        fig_compare.add_trace(go.Bar(x=city_stats.index, y=city_stats['PM2.5 средн'], name='PM2.5 средний'))
        fig_compare.add_trace(go.Bar(x=city_stats.index, y=city_stats['AQI средн'], name='AQI средний'))
        fig_compare.update_layout(title="Сравнение городов", barmode='group', height=400)
        st.plotly_chart(fig_compare, use_container_width=True)
    else:
        st.info("Нет данных")

# Tab 4: Analysis Results
with tab4:
    st.header("🔬 Результаты анализа")
    
    if selected_city != "Все города":
        st.info(f"🔍 Фильтр: **{selected_city}**")
    
    # Получаем анализы
    try:
        response = httpx.get(f"{BACKEND_URL}/api/data/analyses", params={"hours": 168}, timeout=30.0)
        analyses = response.json()
        
        if selected_city != "Все города":
            analyses = [a for a in analyses if extract_city_name(a.get("location_name", "")) == selected_city]
        
        if analyses:
            # Группируем по времени создания (последний анализ)
            latest_analyses = {}
            for a in analyses:
                loc = a.get("location_name")
                if loc not in latest_analyses:
                    latest_analyses[loc] = a
            
            # Показываем детальный анализ от LLM
            if latest_analyses:
                first_analysis = list(latest_analyses.values())[0]
                
                st.markdown("---")
                st.subheader("🤖 Экспертный анализ от AI")
                
                # Краткое резюме в highlight
                st.success(f"**📝 Резюме:** {first_analysis.get('summary', 'N/A')}")
                
                # Детальный анализ в красивом блоке
                detailed = first_analysis.get('detailed_analysis', 'Детальный анализ недоступен.')
                st.markdown(f"""
                <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                            padding: 20px; 
                            border-radius: 10px; 
                            color: white; 
                            margin: 20px 0'>
                    <h3 style='color: white; margin-top: 0'>💬 Мнение AI-эксперта</h3>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(detailed)
                
                st.markdown("---")
            
            # Таблица результатов
            st.subheader("📊 Детальные результаты по локациям")
            
            analysis_df = pd.DataFrame([
                {
                    "Локация": a.get("location_name"),
                    "Тренд PM2.5": a.get("pm25_trend", "N/A"),
                    "Средний PM2.5": f"{a.get('pm25_avg', 0):.1f}",
                    "Аномалии": a.get("anomalies_count", 0),
                    "Дата анализа": pd.to_datetime(a.get("created_at")).strftime("%d.%m.%Y %H:%M") if a.get("created_at") else "N/A"
                }
                for a in latest_analyses.values()
            ])
            
            st.dataframe(analysis_df, use_container_width=True)
            
            # Визуализация
            col1, col2 = st.columns(2)
            
            with col1:
                trend_counts = analysis_df['Тренд PM2.5'].value_counts()
                fig_trends = go.Figure(data=[go.Pie(
                    labels=trend_counts.index,
                    values=trend_counts.values,
                    hole=0.3
                )])
                fig_trends.update_layout(title="Распределение трендов")
                st.plotly_chart(fig_trends, use_container_width=True)
            
            with col2:
                top_anomalies = analysis_df.nlargest(5, 'Аномалии')
                fig_anomalies = go.Figure(data=[go.Bar(
                    x=top_anomalies['Локация'],
                    y=top_anomalies['Аномалии'],
                    marker_color='indianred'
                )])
                fig_anomalies.update_layout(title="Топ-5 локаций по аномалиям")
                st.plotly_chart(fig_anomalies, use_container_width=True)
        else:
            st.warning("⚠️ Нет результатов анализа. Нажмите '📊 Анализ' в боковой панели.")
    except Exception as e:
        st.error(f"Ошибка загрузки анализов: {e}")

# Tab 5: Chat
with tab5:
    st.header("💬 Чат с агентами")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    if prompt := st.chat_input("Задайте вопрос (например: 'Покажи прогноз на завтра')"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Думаю..."):
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

# Tab 6: Data tables
with tab6:
    st.header("📋 Данные")
    
    if selected_city != "Все города":
        st.info(f"🔍 Фильтр: **{selected_city}**")
    
    # Alerts
    st.subheader("🚨 Активные алерты")
    alerts = fetch_alerts()
    if alerts:
        alerts_df = pd.DataFrame(alerts)
        if selected_city != "Все города":
            alerts_df['city'] = alerts_df['location_name'].apply(extract_city_name)
            alerts_df = alerts_df[alerts_df['city'] == selected_city]
        
        if not alerts_df.empty:
            st.dataframe(alerts_df[['location_name', 'severity', 'message', 'created_at']], use_container_width=True)
        else:
            st.success("✅ Нет алертов")
    else:
        st.success("✅ Нет алертов")
    
    # Forecasts
    st.subheader("🔮 Прогнозы")
    forecasts = fetch_forecasts()
    if forecasts:
        forecasts_df = pd.DataFrame(forecasts)
        if selected_city != "Все города":
            forecasts_df['city'] = forecasts_df['location_name'].apply(extract_city_name)
            forecasts_df = forecasts_df[forecasts_df['city'] == selected_city]
        
        if not forecasts_df.empty:
            st.dataframe(forecasts_df[['location_name', 'forecast_time', 'predicted_pm25', 'predicted_aqi']], use_container_width=True)
    else:
        st.info("Нет прогнозов")
    
    # Measurements
    st.subheader("📊 Измерения")
    if measurements:
        measurements_df = pd.DataFrame(measurements[:100])
        st.dataframe(measurements_df[['location_name', 'timestamp', 'pm25', 'pm10', 'temperature']], use_container_width=True)

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: gray;'>
    <small>Eco Monitor v1.0 | LangChain + LangGraph + GROQ | 2026</small>
</div>
""", unsafe_allow_html=True)

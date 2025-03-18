# analytics-dashboard.py
import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import altair as alt
from ftplib import FTP
import tempfile
import os

# FTP beállítások
FTP_HOST = "ftp.pairfect.hu"
FTP_USER = "pairfect"
FTP_PASS = "65Q6sjIhrF"
DB_PATH = "/public_html/api/db/gamedata.db"  # Teljes útvonal

# Oldal konfigurálása
st.set_page_config(
    page_title="PairFect Analytics",
    page_icon="🎮",
    layout="wide"
)

# Adatok lekérdezése cache-eléssel
@st.cache_data(ttl=60)  # 1 percenként frissül
def load_data():
    with st.spinner('Adatok betöltése...'):
        try:
            # Ideiglenes fájl létrehozása
            with tempfile.NamedTemporaryFile(delete=False) as temp_db:
                # FTP kapcsolódás és fájl letöltése
                with FTP(FTP_HOST) as ftp:
                    ftp.login(user=FTP_USER, passwd=FTP_PASS)
                    
                    # Adatbázis letöltése
                    ftp.retrbinary(f'RETR {DB_PATH}', temp_db.write)
            
            # SQLite kapcsolat és adatok beolvasása
            conn = sqlite3.connect(temp_db.name)
            df = pd.read_sql_query("""
                SELECT 
                    id,
                    datetime(timestamp, 'localtime') as timestamp,
                    action,
                    game_file,
                    game_title,
                    score,
                    time,
                    browser_info,
                    screen_size
                FROM game_logs
            """, conn)
            
            conn.close()
            
            # Ideiglenes fájl törlése
            os.unlink(temp_db.name)
            
            return df
            
        except Exception as e:
            st.error(f"Hiba az adatok betöltése során: {str(e)}")
            return pd.DataFrame()

def main():
    st.title("🎮 PairFect Analytics Dashboard")
    
    try:
        # Adatok betöltése
        df = load_data()
        
        if df.empty:
            st.error("Nem sikerült adatokat betölteni!")
            return
            
        # Dátum konvertálása
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Időszak választó és szűrés
        col1, col2 = st.columns(2)
        
        # Minimum és maximum dátumok meghatározása
        min_date = df['timestamp'].min().date()
        max_date = df['timestamp'].max().date()
        
        with col1:
            start_date = st.date_input(
                "Kezdő dátum",
                min_value=min_date,
                max_value=max_date,
                value=min_date
            )
        with col2:
            end_date = st.date_input(
                "Végső dátum",
                min_value=min_date,
                max_value=max_date,
                value=max_date
            )
           
        
        # Dátum konvertálás és szűrés
        start_datetime = pd.Timestamp(start_date)
        end_datetime = pd.Timestamp(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

        # Szűrés
        mask = (df['timestamp'] >= start_datetime) & (df['timestamp'] <= end_datetime)
        df_filtered = df.loc[mask].copy()
        
        
        # Fő metrikák
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_games = len(df_filtered[df_filtered['action'] == 'load'])
            st.metric("Összes játékindítás", total_games)
            
        with col2:
            completed_games = len(df_filtered[df_filtered['action'] == 'complete'])
            st.metric("Befejezett játékok", completed_games)
            
        with col3:
            completion_rate = round((completed_games / total_games * 100 if total_games > 0 else 0), 1)
            st.metric("Befejezési arány", f"{completion_rate}%")
        
        with col4:
            # Utolsó 3 óra időpontjának kiszámítása
            current_time = pd.Timestamp.now()  # Aktuális idő
            last_hours = current_time - pd.Timedelta(hours=3)
            
            # Utolsó 3 óra játékainak számolása
            recent_starts = len(df[  # Az eredeti df-et használjuk, nem a szűrtet
                (df['action'] == 'load') & 
                (df['timestamp'] >= last_hours)
            ])
            recent_completes = len(df[  # Itt is
                (df['action'] == 'complete') & 
                (df['timestamp'] >= last_hours)
            ])
            recent_panics = len(df[  # És itt is
                (df['action'] == 'panic_button') & 
                (df['timestamp'] >= last_hours)
            ])

            # Egy mérőóra három értékkel
            fig = go.Figure()
            
            # Mérőóra létrehozása
            fig.add_trace(go.Indicator(
                mode="gauge",
                value=recent_starts,
                title={
                    'text': "Utolsó 3 óra aktivitása",
                    'font': {'size': 16, 'color': 'white'}
                },
                gauge={
                    'axis': {
                        'range': [0, max(60, recent_starts * 1.2)],
                        'tickwidth': 1,
                        'tickcolor': "white",
                        'tickfont': {'color': 'white'},
                        # Tengely pozicionálás javítása
                        'tickmode': 'array',
                        'tickvals': [0, 20, 40, 60],
                    },
                    'bgcolor': "rgba(0,0,0,0)",
                    'borderwidth': 0,
                    'steps': [
                        {'range': [0, recent_starts], 'color': "rgb(59, 130, 246)", 'thickness': 0.75},
                        {'range': [0, recent_completes], 'color': "rgb(34, 197, 94)", 'thickness': 0.5},
                        {'range': [0, recent_panics], 'color': "rgb(239, 68, 68)", 'thickness': 0.25}
                    ],
                    'bar': {'color': "rgba(0,0,0,0)"}
                }
            ))
            
            # Layout beállítása
            fig.update_layout(
                height=200,
                # Jobb oldali margó növelése
                margin=dict(l=30, r=30, t=40, b=40),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font={'color': "white"},
                # Kontér méretének beállítása
                autosize=False,
                width=400,  # Fix szélesség
                annotations=[
                    dict(
                        text=f'Indítások: {recent_starts}',
                        x=0.5,
                        y=-0.15,
                        showarrow=False,
                        font={'color': 'rgb(59, 130, 246)', 'size': 14}
                    ),
                    dict(
                        text=f'Befejezések: {recent_completes}',
                        x=0.5,
                        y=-0.25,
                        showarrow=False,
                        font={'color': 'rgb(34, 197, 94)', 'size': 14}
                    ),
                    dict(
                        text=f'Pánik: {recent_panics}',
                        x=0.5,
                        y=-0.35,
                        showarrow=False,
                        font={'color': 'rgb(239, 68, 68)', 'size': 14}
                    )
                ]
            )
            st.plotly_chart(fig, use_container_width=True)

        
        # Legutóbbi játékok megjelenítése
        st.markdown("### Legutóbb betöltött játékok")
        recent_games = (df_filtered[df_filtered['action'] == 'load']
                       .sort_values('timestamp', ascending=False)
                       .head(5))
        
        # Játékonként egy kártya
        cols = st.columns(5)
        for idx, (_, game) in enumerate(recent_games.iterrows()):
            with cols[idx]:
                container = st.container()
                container.markdown(f"""
                    <div style='padding: 1rem; 
                                border-radius: 0.5rem; 
                                background-color: #1E1E1E; 
                                border: 1px solid #333;
                                margin: 0.25rem;'>
                        <div style='font-size: 0.9rem; color: #E0E0E0; margin-bottom: 0.5rem;'>
                            {game['game_title']}
                        </div>
                        <div style='font-size: 0.8rem; color: #808080;'>
                            {game['timestamp'].strftime('%Y-%m-%d %H:%M')}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        # Legutóbb befejezett játékok megjelenítése
        st.markdown("### Legutóbb befejezett játékok")
        recent_completions = (df_filtered[df_filtered['action'] == 'complete']
                            .sort_values('timestamp', ascending=False)
                            .head(5))
        
        # Játékonként egy kártya
        cols = st.columns(5)
        for idx, (_, game) in enumerate(recent_completions.iterrows()):
            with cols[idx]:
                container = st.container()
                container.markdown(f"""
                    <div style='padding: 1rem; 
                                border-radius: 0.5rem; 
                                background-color: #1E1E1E; 
                                border: 1px solid #333;
                                margin: 0.25rem;'>
                        <div style='font-size: 0.9rem; color: #E0E0E0; margin-bottom: 0.5rem;'>
                            {game['game_title']}
                        </div>
                        <div style='font-size: 0.8rem; color: #808080;'>
                            {game['timestamp'].strftime('%Y-%m-%d %H:%M')}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        # Legutóbbi pánik gomb használatok
        st.markdown("### Legutóbbi pánik gomb használatok")
        recent_panics = (df_filtered[df_filtered['action'] == 'panic_button']
                        .sort_values('timestamp', ascending=False)
                        .head(5))
        
        # Játékonként egy kártya
        cols = st.columns(5)
        for idx, (_, game) in enumerate(recent_panics.iterrows()):
            with cols[idx]:
                container = st.container()
                container.markdown(f"""
                    <div style='padding: 1rem; 
                                border-radius: 0.5rem; 
                                background-color: #1E1E1E; 
                                border: 1px solid #333;
                                margin: 0.25rem;'>
                        <div style='font-size: 0.9rem; color: #E0E0E0; margin-bottom: 0.5rem;'>
                            {game['game_title']}
                        </div>
                        <div style='font-size: 0.8rem; color: #808080;'>
                            {game['timestamp'].strftime('%Y-%m-%d %H:%M')}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        # Elválasztó a játék kártyák után
        st.markdown("<hr style='margin: 2rem 0; border-color: #333;'>", unsafe_allow_html=True)
        
        # Grafikonok - időbeli eloszlás és legnépszerűbb játékok
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Játékok időbeli eloszlása")
            
            # Külön dataframe-ek létrehozása az egyes eseményekhez
            daily_loads = df_filtered[df_filtered['action'] == 'load'].groupby(
                df_filtered['timestamp'].dt.date).size().reset_index(name='loads')
            
            daily_completes = df_filtered[df_filtered['action'] == 'complete'].groupby(
                df_filtered['timestamp'].dt.date).size().reset_index(name='completes')
            
            daily_panics = df_filtered[df_filtered['action'] == 'panic_button'].groupby(
                df_filtered['timestamp'].dt.date).size().reset_index(name='panics')
            
            # Plotly figure létrehozása
            fig = go.Figure()
            
            # Betöltések vonala (kék)
            fig.add_trace(go.Scatter(
                x=daily_loads['timestamp'],
                y=daily_loads['loads'],
                name='Betöltések',
                line=dict(color='rgb(59, 130, 246)', width=2),
                hovertemplate='Betöltések: %{y}<br>Dátum: %{x}<extra></extra>'
            ))
            
            # Befejezések vonala (zöld)
            fig.add_trace(go.Scatter(
                x=daily_completes['timestamp'],
                y=daily_completes['completes'],
                name='Befejezések',
                line=dict(color='rgb(34, 197, 94)', width=2),
                hovertemplate='Befejezések: %{y}<br>Dátum: %{x}<extra></extra>'
            ))
            
            # Pánik gombok vonala (piros)
            fig.add_trace(go.Scatter(
                x=daily_panics['timestamp'],
                y=daily_panics['panics'],
                name='Pánik gombok',
                line=dict(color='rgb(239, 68, 68)', width=2),
                hovertemplate='Pánik gombok: %{y}<br>Dátum: %{x}<extra></extra>'
            ))
            
            # Layout beállítása
            fig.update_layout(
                title="Napi játékszám típusonként",
                xaxis_title="Dátum",
                yaxis_title="Játékok száma",
                hovermode='x unified',
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("Legnépszerűbb játékok")
            
            # Játékok indítási, befejezési és pánik statisztikái
            starts = df_filtered[df_filtered['action'] == 'load'].groupby('game_title').size()
            completes = df_filtered[df_filtered['action'] == 'complete'].groupby('game_title').size()
            panics = df_filtered[df_filtered['action'] == 'panic_button'].groupby('game_title').size()
            
            # DataFrame létrehozása a három statisztikával
            game_stats = pd.DataFrame({
                'Indítások': starts,
                'Befejezések': completes,
                'Pánik': panics
            }).fillna(0).sort_values('Indítások', ascending=True).tail(10)
            
            # Plotly figure létrehozása
            fig = go.Figure()
            
            # Indítások hozzáadása
            fig.add_trace(go.Bar(
                name='Indítások',
                y=game_stats.index,
                x=game_stats['Indítások'],
                orientation='h',
                marker_color='rgb(59, 130, 246)',  # Kék
                marker_line=dict(width=0),
                hovertemplate='Indítások: %{x}<br>Játék: %{y}<extra></extra>'
            ))
            
            # Befejezések hozzáadása
            fig.add_trace(go.Bar(
                name='Befejezések',
                y=game_stats.index,
                x=game_stats['Befejezések'],
                orientation='h',
                marker_color='rgb(34, 197, 94)',  # Zöld
                marker_line=dict(width=0),
                hovertemplate='Befejezések: %{x}<br>Játék: %{y}<extra></extra>'
            ))

            # Pánik hozzáadása
            fig.add_trace(go.Bar(
                name='Pánik',
                y=game_stats.index,
                x=game_stats['Pánik'],
                orientation='h',
                marker_color='rgb(239, 68, 68)',  # Piros
                marker_line=dict(width=0),
                hovertemplate='Pánik: %{x}<br>Játék: %{y}<extra></extra>'
            ))
            
            # Layout beállítása
            fig.update_layout(
                title="Top 10 legnépszerűbb játék",
                barmode='group',
                height=400,
                margin=dict(l=0, r=0, t=40, b=0),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                ),
                xaxis_title="Játékok száma",
                hovermode='closest'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        # Elválasztó a böngésző statisztikák előtt
        st.markdown("<hr style='margin: 2rem 0; border-color: #333;'>", unsafe_allow_html=True)
        
        # Böngésző és eszköz statisztikák
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Böngésző használat")
            
            # Böngésző adatok egyszerűsítése
            def simplify_browser(browser_info):
                if 'Chrome' in browser_info:
                    if 'Mobil' in browser_info:
                        return 'Chrome (Mobil)'
                    return 'Chrome (Asztali)'
                elif 'Safari' in browser_info:
                    if 'Mobil' in browser_info:
                        return 'Safari (Mobil)'
                    return 'Safari (Asztali)'
                elif 'Firefox' in browser_info:
                    return 'Firefox'
                elif 'Edge' in browser_info:
                    return 'Edge'
                elif 'Mozilla' in browser_info:
                    if 'Mobile' in browser_info or 'iPhone' in browser_info:
                        return 'Egyéb (Mobil)'
                    return 'Egyéb (Asztali)'
                else:
                    return 'Egyéb'

            # Böngészők csoportosítása
            df_filtered['simplified_browser'] = df_filtered['browser_info'].apply(simplify_browser)
            browser_stats = df_filtered['simplified_browser'].value_counts()
            
            # Kördiagram létrehozása
            fig = go.Figure(data=[go.Pie(
                labels=browser_stats.index,
                values=browser_stats.values,
                hole=0.3,
                marker=dict(colors=['rgb(59, 130, 246)',   # Kék
                                  'rgb(34, 197, 94)',      # Zöld
                                  'rgb(239, 68, 68)',      # Piros
                                  'rgb(168, 85, 247)',     # Lila
                                  'rgb(251, 191, 36)',     # Sárga
                                  'rgb(236, 72, 153)']),   # Rózsaszín
            )])
            
            fig.update_layout(
                title="Böngésző eloszlás",
                showlegend=True,
                legend=dict(
                    orientation="v",
                    yanchor="middle",
                    y=0.5,
                    xanchor="right",
                    x=1.1
                ),
                margin=dict(l=0, r=120, t=40, b=0),
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("Képernyőméretek")
            screen_stats = df_filtered['screen_size'].value_counts().head(10)
            fig = px.bar(screen_stats,
                        title="Leggyakoribb képernyőméretek",
                        labels={'value': 'Darabszám', 'index': 'Képernyőméret'})
            st.plotly_chart(fig, use_container_width=True)

        # Pánik gomb használati statisztikák
        st.subheader("Pánik gomb használati statisztikák")
        col1, col2 = st.columns(2)
        
        with col1:
            # Pánik gomb használat időbeli eloszlása
            panic_over_time = df_filtered[df_filtered['action'] == 'panic_button'].groupby(
                df_filtered['timestamp'].dt.date).size().reset_index()
            panic_over_time.columns = ['date', 'count']
            
            fig = px.line(panic_over_time, x='date', y='count',
                         title="Pánik gomb használat időbeli eloszlása",
                         labels={'count': 'Használatok száma', 'date': 'Dátum'})
            st.plotly_chart(fig, use_container_width=True)
            
        with col2:
            # Pánik/Befejezés arány játékonként
            panic_rate = pd.DataFrame({
                'Játék': game_stats.index,
                'Pánik arány': (game_stats['Pánik'] / game_stats['Indítások'] * 100).round(1)
            }).sort_values('Pánik arány', ascending=True)
            
            fig = px.bar(panic_rate,
                        x='Pánik arány',
                        y='Játék',
                        orientation='h',
                        title="Pánik gomb használati arány játékonként (%)",
                        labels={'Pánik arány': 'Használati arány (%)'})
            st.plotly_chart(fig, use_container_width=True)

        # Elválasztó a részletes elemzés előtt
        st.markdown("<hr style='margin: 2rem 0; border-color: #333;'>", unsafe_allow_html=True)
        
        # Nyers adatok megjelenítése
        st.subheader("Nyers adatok")
        if st.checkbox("Mutasd a nyers adatokat"):
            # Adatok formázása a megjelenítéshez
            display_df = df_filtered.copy()
            display_df['timestamp'] = display_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # Oszlopok átnevezése a jobb érthetőség érdekében
            display_df = display_df.rename(columns={
                'timestamp': 'Időpont',
                'action': 'Művelet',
                'game_file': 'Játék fájl',
                'game_title': 'Játék címe',
                'score': 'Pontszám',
                'time': 'Játékidő',
                'browser_info': 'Böngésző',
                'screen_size': 'Képernyőméret'
            })
            
            # Műveletek magyarítása
            display_df['Művelet'] = display_df['Művelet'].map({
                'load': 'Betöltés',
                'complete': 'Befejezés',
                'panic_button': 'Pánik gomb használat'
            })
            
            st.dataframe(display_df)
            
    except Exception as e:
        st.error(f"Hiba történt: {str(e)}")

if __name__ == "__main__":
    main()
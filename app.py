import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import folium
from streamlit_folium import st_folium

# 1. 페이지 설정 (아이콘 및 레이아웃)
st.set_page_config(page_title="SubwayFacility", layout="wide", page_icon="🚇")

# 2. DB 연결 함수 (Streamlit Secrets 활용)
@st.cache_resource
def get_db_connection():
    try:
        # Streamlit Cloud의 Secrets 설정에서 정보를 읽어옵니다.
        db_info = st.secrets["postgres"]
        return psycopg2.connect(
            host=db_info["host"],
            database=db_info["database"],
            user=db_info["user"],
            password=db_info["password"],
            port=db_info["port"],
            connect_timeout=5  # 연결 시도 시간 제한 (무한 로딩 방지)
        )
    except Exception as e:
        st.error(f"데이터베이스 연결 설정 오류: {e}")
        return None

# 3. 데이터 조회 함수 (캐싱 적용)
@st.cache_data(ttl=600)
def fetch_search_data(stn_name, kind_name):
    conn = get_db_connection()
    if conn is None: return []
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        query = "SELECT * FROM station_facilities WHERE 1=1"
        params = []
        if stn_name:
            query += " AND stn_nm = %s"
            params.append(stn_name)
        if kind_name != "전체":
            query += " AND fclt_kind = %s"
            params.append(kind_name)
        query += " ORDER BY stn_nm ASC"
        cur.execute(query, params)
        return cur.fetchall()

# --- 사이드바 안내 ---
with st.sidebar:
    st.title("🚇 SubwayFacility")
    st.info("해당 사이트는 서울교통공사 운영 역 (2~8호선) 내 시설정보만 제공합니다.")
    st.caption("Update Cycle: Daily 08:00 / 18:00")

# --- 메인 탭 구성 ---
tabs = st.tabs(["🔍 실시간 시설물 조회", "📜 최근 변경 이력"])

# 탭 1: 실시간 조회
with tabs[0]:
    col1, col2 = st.columns([1, 1.5])
    
    with col1:
        st.subheader("Smart Search")
        
        # 역 명단 로딩
        conn = get_db_connection()
        if conn:
            df_stns = pd.read_sql("SELECT DISTINCT stn_nm FROM station_facilities ORDER BY stn_nm", conn)
            stn_list = [""] + list(df_stns['stn_nm'])
        else:
            stn_list = [""]
            
        target_stn = st.selectbox("역 이름을 선택하세요", stn_list)
        target_kind = st.selectbox("시설 종류", ["전체", "엘리베이터", "에스컬레이터", "화장실", "수유실", "물품보관함"])
        
        if st.button("조회 시작", use_container_width=True):
            if not target_stn:
                st.warning("역을 먼저 선택해 주세요.")
            else:
                results = fetch_search_data(target_stn, target_kind)
                if results:
                    st.success(f"{len(results)}건의 정보를 찾았습니다.")
                    for item in results:
                        status = "🟢 구동중" if item['oprtng_situ'] in ['M', '정상', 'Y'] else "🔴 점검중"
                        with st.expander(f"{item['fclt_kind']} ({status})"):
                            st.write(f"**위치:** {item['dtl_pstn']}")
                            st.caption(f"최종 갱신: {item['updated_at']}")
                else:
                    st.error("갱신 시점 기준 데이터가 없습니다.")

    with col2:
        st.subheader("역 위치 안내")
        m = folium.Map(location=[37.5665, 126.9780], zoom_start=13)
        # 여기에 검색 결과 기반 핀 추가 로직 확장 가능
        st_folium(m, width="100%", height=500)

# 탭 2: 변경 이력
with tabs[1]:
    st.subheader("최근 24시간 업데이트 내역")
    if conn:
        df_hist = pd.read_sql("""
            SELECT line_nm as 호선, stn_nm as 역명, fclt_kind as 종류, oprtng_situ as 상태, updated_at as 갱신시각 
            FROM station_facilities 
            WHERE updated_at >= NOW() - INTERVAL '24 hours' 
            ORDER BY updated_at DESC
        """, conn)
        
        if not df_hist.empty:
            st.dataframe(df_hist, use_container_width=True, hide_index=True)
        else:
            st.info("최근 24시간 내 변경 사항이 없습니다.")

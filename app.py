import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import folium
from streamlit_folium import st_folium

# 1. 페이지 설정
st.set_page_config(page_title="SubwayFacility", layout="wide", page_icon="🚇")

# 2. DB 연결 캐싱 (중요: 조회가 빨라지는 핵심)
@st.cache_resource
def get_db_connection():
    return psycopg2.connect(
        host="mobility-techplan-postgre.ay1.krane.9rum.cc",
        database="techplan",
        user="postgres",
        password="rltnfrlghlrxla1!",
        port="5432"
    )

# 3. 데이터 조회 로직 (10분간 결과 캐싱)
@st.cache_data(ttl=600)
def fetch_data(stn_name, kind_name):
    conn = get_db_connection()
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

# 4. 사이드바 구성
with st.sidebar:
    st.title("🚇 SubwayFacility")
    st.info("서울교통공사 운영 역 (2~8호선) 내 시설정보")
    st.markdown("---")
    st.caption("데이터 정기 업데이트: 08:00 / 18:00")

# 5. 메인 화면 구성
tabs = st.tabs(["🔍 실시간 조회", "📜 변경 이력"])

with tabs[0]:
    col1, col2 = st.columns([1, 1.5])
    
    with col1:
        st.subheader("시설물 검색")
        # 모든 역 명단 가져오기 (자동완성용)
        conn = get_db_connection()
        all_stns = pd.read_sql("SELECT DISTINCT stn_nm FROM station_facilities ORDER BY stn_nm", conn)
        
        target_stn = st.selectbox("역 이름을 선택하세요", [""] + list(all_stns['stn_nm']))
        target_kind = st.selectbox("시설 종류", ["전체", "엘리베이터", "에스컬레이터", "화장실", "수유실", "물품보관함"])
        
        if st.button("조회하기", use_container_width=True):
            if not target_stn:
                st.warning("역 이름을 선택해 주세요.")
            else:
                results = fetch_data(target_stn, target_kind)
                if results:
                    st.success(f"{len(results)}개의 시설을 찾았습니다.")
                    for item in results:
                        status = "🟢 정상" if item['oprtng_situ'] in ['M', '정상', 'Y'] else "🔴 점검/중지"
                        with st.expander(f"{item['fclt_kind']} ({status})"):
                            st.write(f"**상세위치:** {item['dtl_pstn']}")
                            st.caption(f"최종 업데이트: {item['updated_at']}")
                else:
                    st.error("해당하는 시설 정보가 없습니다.")

    with col2:
        st.subheader("역 위치 확인")
        # 기본 위치 설정
        m = folium.Map(location=[37.5665, 126.9780], zoom_start=13)
        st_folium(m, width="100%", height=500)

with tabs[1]:
    st.subheader("최근 24시간 변경 사항")
    df_hist = pd.read_sql("""
        SELECT line_nm as 호선, stn_nm as 역명, fclt_kind as 종류, oprtng_situ as 상태, updated_at as 갱신시간 
        FROM station_facilities 
        WHERE updated_at >= NOW() - INTERVAL '24 hours' 
        ORDER BY updated_at DESC
    """, conn)
    
    if not df_hist.empty:
        st.dataframe(df_hist, use_container_width=True, hide_index=True)
    else:
        st.info("최근 24시간 내 변경된 정보가 없습니다.")

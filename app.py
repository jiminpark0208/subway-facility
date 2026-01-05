import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import folium
from streamlit_folium import st_folium
from datetime import datetime, timedelta

# 페이지 설정
st.set_page_config(page_title="SubwayFacility", layout="wide")

# CSS로 상단 공지사항 스타일 잡기
st.markdown("""
    <style>
    .notice { font-size: 12px; color: #666; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# DB 연결 함수 (연결 유지)
@st.cache_resource
def get_connection():
    return psycopg2.connect(
        host="mobility-techplan-postgre.ay1.krane.9rum.cc",
        database="techplan",
        user="postgres",
        password="rltnfrlghlrxla1!",
        port="5432"
    )

# 사이드바 설정
with st.sidebar:
    st.title("🚇 SubwayFacility")
    st.markdown('<p class="notice">해당 사이트는 서울교통공사 운영 역 (경원경인선, 2~8호선) 내 시설정보만 제공합니다.</p>', unsafe_allow_html=True)
    st.divider()
    st.info("데이터는 매일 오전 8시, 오후 6시에 정기 업데이트됩니다.")

# 메인 탭 구성
tabs = st.tabs(["🔍 실시간 시설물 조회", "📜 최근 변경 이력"])

# --- 탭 1: 실시간 조회 ---
with tabs[0]:
    col1, col2 = st.columns([1, 1.5])
    
    with col1:
        st.subheader("검색 필터")
        with st.form("search_form"):
            line_input = st.text_input("호선 입력 (예: 2호선)")
            stn_input = st.text_input("역 이름 입력")
            kind_input = st.selectbox("시설물 종류", ["전체", "엘리베이터", "에스컬레이터", "화장실", "수유실", "물품보관함", "무인민원발급기", "ATM", "유실물보관소", "승차권자동발매기", "고객안전실", "또타러기지", "도서판매대", "환승주차장", "문화시설", "자전거보관함"])
            submitted = st.form_submit_button("조회하기")

        if submitted:
            conn = get_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            query = "SELECT * FROM station_facilities WHERE 1=1"
            params = []
            if line_input: query += " AND line_nm LIKE %s"; params.append(f"%{line_input}%")
            if stn_input: query += " AND stn_nm LIKE %s"; params.append(f"%{stn_input}%")
            if kind_input != "전체": query += " AND fclt_kind = %s"; params.append(kind_input)
            
            cur.execute(query, params)
            results = cur.fetchall()
            
            if results:
                st.success(f"{len(results)}개의 시설물이 검색되었습니다.")
                for item in results:
                    status_icon = "🟢" if item['oprtng_situ'] in ['M', '정상', 'Y', '구동중'] else "🔴"
                    with st.expander(f"{status_icon} {item['stn_nm']} - {item['fclt_kind']}"):
                        st.write(f"**상세 위치:** {item['dtl_pstn']}")
                        st.write(f"**운영 상태:** {item['oprtng_situ']}")
                        st.write(f"**최종 갱신:** {item['updated_at']}")
            else:
                st.warning("검색 결과가 없습니다.")

    with col2:
        st.subheader("시설물 위치 확인")
        # 기본 위치 서울역
        m = folium.Map(location=[37.5665, 126.9780], zoom_start=12)
        st_folium(m, width="100%", height=600)

# --- 탭 2: 변경 이력 ---
with tabs[1]:
    st.subheader("최근 24시간 변경 내역")
    conn = get_connection()
    query_hist = """
        SELECT line_nm, stn_nm, fclt_kind, oprtng_situ, updated_at 
        FROM station_facilities 
        WHERE updated_at >= NOW() - INTERVAL '1 day' 
        ORDER BY updated_at DESC
    """
    df = pd.read_sql(query_hist, conn)
    
    if not df.empty:
        # 최신 갱신일 추출
        last_sync = df['updated_at'].max()
        st.metric("최종 동기화 시점", value=str(last_sync))
        st.dataframe(df, use_container_width=True)
    else:
        st.error("갱신 시점 기준 변경사항이 없습니다.")
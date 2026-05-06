import streamlit as st
import sqlite3
import pandas as pd
import os

# 1. 웹페이지 기본 설정 (제목, 레이아웃 넓게 쓰기)
st.set_page_config(page_title="따릉이 공공데이터 대시보드", layout="wide")
st.title("🚲 서울시 따릉이 공공데이터 분석 대시보드")
st.write("공공데이터를 활용해 따릉이 이용 패턴을 분석한 결과입니다.")

# 2. 데이터베이스 파일 확인 (친절한 에러 메시지)
db_path = 'bicycle.db'
if not os.path.exists(db_path):
    st.error("앗! 데이터베이스 파일을 찾을 수 없어요. 😢")
    st.warning("현재 폴더에 'bicycle.db' 파일이 있는지 확인해 주세요. 파일이 있어야 분석을 시작할 수 있습니다!")
    st.stop() # 파일이 없으면 여기서 프로그램 실행을 멈춥니다.

# 3. 데이터베이스에서 데이터를 가져오는 마법의 함수
@st.cache_data # 데이터를 매번 다시 불러오지 않고 기억해두는 기능(속도 향상!)
def load_data(query):
    conn = sqlite3.connect(db_path) # DB와 연결!
    df = pd.read_sql(query, conn)   # SQL 질문을 던져서 표(DataFrame) 형태로 받기
    conn.close()                    # 연결 종료
    return df

st.divider() # 구분선 찍기

# ==========================================
# 차트 1. 월별 이용패턴
# ==========================================
st.header("📈 1. 월별 따릉이 이용 패턴")

# SQL 쿼리: 대여일자(년월)별로 이용건수를 모두 더합니다.
sql_1 = """
SELECT 
    대여일자 AS 월, 
    SUM(이용건수) AS 총이용건수 
FROM 이용정보 
GROUP BY 대여일자 
ORDER BY 대여일자
"""
df_1 = load_data(sql_1)

col1, col2 = st.columns([2, 1]) # 화면을 2:1 비율로 나눕니다.

with col1:
    # ① 시각화: 라인 차트
    st.line_chart(df_1.set_index('월'))

with col2:
    # ② 사용한 SQL 보여주기
    st.write("**사용된 SQL**")
    st.code(sql_1, language="sql")
    
    # ③ 인사이트 (2~3줄)
    st.info("""
    💡 **데이터 인사이트**
    - 봄(4~5월)과 가을(9~10월)에 이용량이 가장 높게 나타나는 전형적인 계절적 패턴을 보입니다.
    - 한겨울이나 장마철에는 이용량이 급감하므로, 이 시기에는 자전거 정비 및 교체 작업에 집중하는 것이 좋습니다.
    """)

st.divider()

# ==========================================
# 차트 2. 기온별 평균 이용량
# ==========================================
st.header("🌡️ 2. 기온별 평균 이용량")

# SQL 쿼리: 기온을 5도로 나눈 몫에 다시 5를 곱해 5도 단위의 구간을 만듭니다.
sql_2 = """
SELECT 
    (CAST(T.평균기온 / 5 AS INTEGER) * 5) AS 온도대,
    AVG(U.이용건수) AS 평균이용건수
FROM 이용정보 U
JOIN 기온 T ON U.대여일자 = T.년월
GROUP BY 온도대
ORDER BY 온도대
"""
df_2 = load_data(sql_2)
# 차트에 예쁘게 표시하기 위해 '15도~20도' 같은 형태로 이름을 바꿔줍니다.
df_2['기온구간'] = df_2['온도대'].astype(str) + '도 ~ ' + (df_2['온도대'] + 4).astype(str) + '도'

col3, col4 = st.columns([2, 1])

with col3:
    # ① 시각화: 막대 차트
    st.bar_chart(df_2.set_index('기온구간')['평균이용건수'])

with col4:
    # ② 사용한 SQL
    st.write("**사용된 SQL**")
    st.code(sql_2, language="sql")
    
    # ③ 인사이트 (2~3줄)
    st.info("""
    💡 **데이터 인사이트**
    - 평균기온 15도~25도 사이의 온화한 날씨에서 사람들의 자전거 이용이 가장 활발합니다.
    - 영하로 떨어지는 혹한기나 30도에 육박하는 폭염 기간에는 평균 이용량이 절반 이하로 떨어집니다.
    """)

st.divider()

# ==========================================
# 차트 3. 인기 대여소 TOP 10
# ==========================================
st.header("🏆 3. 인기 대여소 TOP 10")

# SQL 쿼리: 이용정보와 대여소를 연결(JOIN)하여 어느 대여소에서 가장 많이 빌렸는지 상위 10개를 뽑습니다.
sql_3 = """
SELECT 
    S.보관소명, 
    SUM(U.이용건수) AS 총이용건수 
FROM 이용정보 U
JOIN 대여소 S ON U.대여소번호 = S.대여소번호
GROUP BY S.대여소번호, S.보관소명
ORDER BY 총이용건수 DESC
LIMIT 10
"""
df_3 = load_data(sql_3)

col5, col6 = st.columns([2, 1])

with col5:
    # ① 시각화: 가로 막대 차트 (가장 많은 곳이 위로 오도록 정렬)
    df_3_sorted = df_3.sort_values('총이용건수', ascending=True)
    st.bar_chart(df_3_sorted.set_index('보관소명'), horizontal=True)

with col6:
    # ② 사용한 SQL
    st.write("**사용된 SQL**")
    st.code(sql_3, language="sql")
    
    # ③ 인사이트 (2~3줄)
    st.info("""
    💡 **데이터 인사이트**
    - 한강 공원 주변이나 주요 지하철역 환승 거점에 위치한 대여소의 이용률이 압도적으로 높습니다.
    - 이 TOP 10 대여소들은 출퇴근 및 레저 목적의 수요가 겹치는 곳으로, 자전거 재배치(보충) 1순위 지역입니다.
    """)
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from PIL import Image
import numpy as np

# 바코드 라이브러리 (배포 환경 호환성을 위해 try-except 처리)
try:
    from pyzbar.pyzbar import decode
    ZBAR_AVAILABLE = True
except ImportError:
    ZBAR_AVAILABLE = False

# --- 1. 페이지 설정 ---
st.set_page_config(
    page_title="편의점 꿀조합 계산기",
    page_icon="🏪",
    layout="mobile" # 모바일 친화적 레이아웃
)

# --- 2. 데이터 로드 (샘플 데이터 + CSV 업로드) ---
@st.cache_data
def load_data():
    # 실제로는 식약처 데이터를 정제한 CSV를 읽어야 하지만, 
    # 데모를 위해 핵심 편의점 상품 데이터를 내장합니다.
    data = {
        '상품명': ['불닭볶음면', '참치마요 삼각김밥', '반숙란(2구)', '자이언트 떡볶이', '바나나우유', '제로콜라', '핫바(매운맛)', '모짜렐라 치즈'],
        '바코드': ['8801043014817', '8801056030018', '8801056030025', '8801056030032', '8801056030049', '8801056030056', '8801056030063', '8801056030070'],
        '카테고리': ['면류', '즉석식품', '가공식품', '즉석식품', '음료', '음료', '가공식품', '유가공'],
        '열량(kcal)': [530, 250, 120, 680, 210, 0, 180, 180],
        '나트륨(mg)': [1280, 480, 300, 1800, 110, 10, 650, 220],
        '탄수화물(g)': [85, 40, 2, 140, 27, 0, 12, 0],
        '단백질(g)': [12, 6, 12, 14, 7, 0, 9, 15],
        '당류(g)': [7, 3, 1, 35, 27, 0, 5, 0]
    }
    return pd.DataFrame(data)

df = load_data()

# --- 3. 세션 상태 초기화 (장바구니) ---
if 'cart' not in st.session_state:
    st.session_state.cart = []

def add_to_cart(item):
    st.session_state.cart.append(item)
    st.toast(f"🛒 '{item['상품명']}' 추가됨!")

def remove_from_cart(index):
    del st.session_state.cart[index]
    st.rerun()

# --- 4. 메인 UI ---
st.title("🏪 편의점 영양사")
st.markdown("오늘 먹을 **꿀조합**의 영양성분을 계산해드립니다.")

# 탭 구성
tab1, tab2, tab3 = st.tabs(["🔍 상품 검색", "📸 바코드 스캔", "🛒 내 장바구니"])

# [Tab 1] 텍스트 검색 및 리스트
with tab1:
    search_query = st.text_input("상품명 검색", placeholder="예: 불닭, 라면...")
    
    if search_query:
        filtered_df = df[df['상품명'].str.contains(search_query)]
    else:
        filtered_df = df

    st.subheader("상품 목록")
    for idx, row in filtered_df.iterrows():
        with st.container():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**{row['상품명']}** ({row['열량(kcal)']} kcal)")
                st.caption(f"나트륨: {row['나트륨(mg)']}mg | 단백질: {row['단백질(g)']}g")
            with col2:
                if st.button("담기", key=f"add_{idx}"):
                    add_to_cart(row)
            st.divider()

# [Tab 2] 바코드/사진 스캔
with tab2:
    st.info("상품의 바코드가 잘 보이게 사진을 찍거나 업로드하세요.")
    uploaded_file = st.file_uploader("사진 업로드", type=['jpg', 'png', 'jpeg'])

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption='업로드된 사진', width=300)
        
        if ZBAR_AVAILABLE:
            try:
                decoded_objects = decode(image)
                if decoded_objects:
                    barcode_data = decoded_objects[0].data.decode("utf-8")
                    st.success(f"바코드 인식 성공: {barcode_data}")
                    
                    # DB에서 검색
                    found_item = df[df['바코드'] == barcode_data]
                    if not found_item.empty:
                        item = found_item.iloc[0]
                        st.success(f"찾은 상품: {item['상품명']}")
                        if st.button("이 상품 장바구니에 담기"):
                            add_to_cart(item)
                    else:
                        st.error("데이터베이스에 없는 상품입니다.")
                else:
                    st.warning("사진에서 바코드를 찾을 수 없습니다. 더 선명한 사진을 써주세요.")
            except Exception as e:
                st.error(f"바코드 처리 중 오류 발생: {e}")
        else:
            st.error("서버에 바코드 인식 라이브러리(zbar)가 설치되지 않았습니다.")
            st.caption("로컬 테스트 중이라면 'brew install zbar' 또는 'sudo apt-get install libzbar0'이 필요합니다.")

# [Tab 3] 장바구니 및 결과 분석
with tab3:
    if not st.session_state.cart:
        st.info("장바구니가 비어있습니다. 상품을 담아보세요!")
    else:
        # 1. 담은 목록 표시
        st.subheader(f"담은 상품 ({len(st.session_state.cart)}개)")
        for i, item in enumerate(st.session_state.cart):
            col1, col2 = st.columns([4, 1])
            col1.text(f"- {item['상품명']}")
            if col2.button("삭제", key=f"del_{i}"):
                remove_from_cart(i)
        
        st.divider()

        # 2. 영양 성분 합산
        total_kcal = sum(item['열량(kcal)'] for item in st.session_state.cart)
        total_sodium = sum(item['나트륨(mg)'] for item in st.session_state.cart)
        total_sugar = sum(item['당류(g)'] for item in st.session_state.cart)
        total_protein = sum(item['단백질(g)'] for item in st.session_state.cart)

        # 3. 기준치 대비 분석 (성인 기준 대략적 수치)
        TARGET = {'kcal': 2000, 'sodium': 2000, 'sugar': 50, 'protein': 55}
        
        st.subheader("📊 영양 분석 결과")
        
        # 칼로리 게이지
        st.metric("총 칼로리", f"{total_kcal} kcal", delta=f"{TARGET['kcal'] - total_kcal} kcal 남음")
        
        # 나트륨 경고 시스템
        sodium_pct = (total_sodium / TARGET['sodium']) * 100
        sodium_color = "red" if sodium_pct > 100 else "green"
        
        st.write(f"**나트륨 (Sodium)**: {total_sodium}mg ({sodium_pct:.1f}%)")
        if sodium_pct > 100:
            st.error("🚨 나트륨 폭발! 오늘 더 이상 짠 음식은 안 돼요!")
            st.write("💡 추천: 바나나우유나 코코넛워터로 나트륨 배출을 도우세요.")
        else:
            st.progress(sodium_pct / 100)

        # 탄단지 차트 (Plotly)
        st.subheader("영양소 비율")
        fig = go.Figure(data=[go.Pie(
            labels=['탄수화물', '단백질', '지방(추정)'], 
            values=[
                sum(item['탄수화물(g)'] for item in st.session_state.cart),
                total_protein,
                sum(item.get('지방(g)', 0) for item in st.session_state.cart) # 데이터에 없으면 0
            ],
            hole=.3
        )])
        fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=200)
        st.plotly_chart(fig, use_container_width=True)

        # 꿀조합 저장 버튼 (기능 예시)
        if st.button("이 조합 저장하기 (나만의 꿀조합)"):
            st.balloons()
            st.success("저장되었습니다! (데모 기능)")

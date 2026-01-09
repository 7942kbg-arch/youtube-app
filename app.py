import streamlit as st
import pandas as pd
from googleapiclient.discovery import build

# ==========================================
# [설정] API 키
# ==========================================
API_KEY = "AIzaSyCdvHrJntPbzY4A_-LD2byHikj2arwlgUc"

st.set_page_config(page_title="Hiview Pro", layout="wide")

# [스타일] 화면을 더 넓고 깔끔하게
st.markdown("""
    <style>
    .block-container { padding-top: 1rem; max-width: 95%; }
    </style>
""", unsafe_allow_html=True)

@st.cache_data
def get_data(keyword):
    try:
        youtube = build('youtube', 'v3', developerKey=API_KEY)
        
        # 1. 영상 검색
        search = youtube.search().list(q=keyword, part="id,snippet", maxResults=50, type="video").execute()
        v_ids = [i['id']['videoId'] for i in search['items']]
        if not v_ids: return []
        
        # 2. 영상 상세 (조회수, 좋아요, 댓글)
        videos = youtube.videos().list(part="snippet,statistics", id=','.join(v_ids)).execute()
        
        # 3. 채널 상세 (구독자, 총 영상 수)
        c_ids = list(set([i['snippet']['channelId'] for i in videos['items']]))
        c_stats = {}
        if c_ids:
            # 채널이 많으면 50개씩 끊어야 함 (간략 처리)
            channels = youtube.channels().list(part="statistics", id=','.join(c_ids[:50])).execute()
            c_stats = {i['id']: i['statistics'] for i in channels['items']}

        data = []
        for item in videos['items']:
            stat = item['statistics']
            snip = item['snippet']
            c_id = snip['channelId']
            
            # 데이터 추출
            views = int(stat.get('viewCount', 0))
            likes = int(stat.get('likeCount', 0))
            comments = int(stat.get('commentCount', 0))
            
            ch_info = c_stats.get(c_id, {})
            subs = int(ch_info.get('subscriberCount', 0))
            total_videos = int(ch_info.get('videoCount', 0))
            
            # [등급 계산]
            # 공헌도 (구독자 대비 조회수 기여도)
            ratio = (views / subs) if subs > 0 else 0
            contrib = "🌱"
            if ratio > 0.5: contrib = "🌿"
            if ratio > 1.0: contrib = "🔥"
            if ratio > 3.0: contrib = "🚀"

            # 실적도 (조회수 절대값)
            perf = "🥉"
            if views > 10000: perf = "🥈"
            if views > 100000: perf = "🥇"
            if views > 1000000: perf = "👑"

            data.append({
                "썸네일": snip['thumbnails']['default']['url'],
                "제목": snip['title'],
                "조회수": views,
                "구독자": subs,
                "실적": perf,
                "공헌": contrib,
                "게시일": snip['publishedAt'][:10],
                "좋아요": likes,
                "댓글": comments,
                "채널영상수": total_videos,
                "링크": f"https://www.youtube.com/watch?v={item['id']}"
            })
        return data
    except Exception as e:
        return []

# ==========================================
# [화면 구성]
# ==========================================
st.title("📊 YouTube 분석기 (Pro Ver)")

# 검색창
with st.container():
    c1, c2 = st.columns([5, 1])
    keyword = c1.text_input("검색어 입력", placeholder="예: 스마트스토어 꿀팁", label_visibility="collapsed")
    run_btn = c2.button("🔍 검색", type="primary", use_container_width=True)

if keyword or run_btn:
    if not keyword:
        st.warning("검색어를 입력해주세요.")
    else:
        with st.spinner("데이터를 분석하고 있습니다..."):
            result = get_data(keyword)
            
            if result:
                st.success(f"검색 결과: {len(result)}개")
                df = pd.DataFrame(result)

                # [핵심] 엑셀 같은 테이블 그리기 (정렬 가능!)
                st.data_editor(
                    df,
                    column_config={
                        "썸네일": st.column_config.ImageColumn("썸네일", width="small"),
                        "제목": st.column_config.TextColumn("제목", width="large"),
                        "조회수": st.column_config.NumberColumn("조회수", format="%d회"),
                        "구독자": st.column_config.NumberColumn("구독자", format="%d명"),
                        "실적": st.column_config.TextColumn("실적", help="조회수 성과"),
                        "공헌": st.column_config.TextColumn("공헌", help="구독자 대비 조회수"),
                        "좋아요": st.column_config.NumberColumn("좋아요", format="%d개"),
                        "댓글": st.column_config.NumberColumn("댓글", format="%d개"),
                        "채널영상수": st.column_config.NumberColumn("총 영상수", format="%d개"),
                        "링크": st.column_config.LinkColumn("링크", display_text="보러가기"),
                    },
                    hide_index=True,       # 0,1,2 숫자 숨김
                    use_container_width=True, # 화면 꽉 차게
                    height=800,            # 표 높이
                    disabled=True          # 내용 수정 금지 (보기 전용)
                )
            else:
                st.error("검색 결과가 없습니다.")

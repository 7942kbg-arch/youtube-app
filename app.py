import streamlit as st
from googleapiclient.discovery import build

# ==========================================
# [설정] API 키 (여기에 본인 키가 들어있습니다)
# ==========================================
API_KEY = "AIzaSyCdvHrJntPbzY4A_-LD2byHikj2arwlgUc"

st.set_page_config(page_title="Hiview Lite", layout="wide")

# 스타일 적용
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 5px; }
    </style>
""", unsafe_allow_html=True)

@st.cache_data
def get_data(keyword):
    try:
        youtube = build('youtube', 'v3', developerKey=API_KEY)
        search = youtube.search().list(q=keyword, part="id,snippet", maxResults=30, type="video").execute()
        v_ids = [i['id']['videoId'] for i in search['items']]
        if not v_ids: return []
        
        videos = youtube.videos().list(part="snippet,statistics", id=','.join(v_ids)).execute()
        
        c_ids = list(set([i['snippet']['channelId'] for i in videos['items']]))
        c_stats = {}
        if c_ids:
            channels = youtube.channels().list(part="statistics", id=','.join(c_ids[:50])).execute()
            c_stats = {i['id']: i['statistics'] for i in channels['items']}

        data = []
        for item in videos['items']:
            stat = item['statistics']
            snip = item['snippet']
            c_id = snip['channelId']
            
            views = int(stat.get('viewCount', 0))
            subs = int(c_stats.get(c_id, {}).get('subscriberCount', 1))
            
            ratio = (views / subs) if subs > 0 else 0
            contrib = "🌱보통"
            if ratio > 0.5: contrib = "🌿양호"
            if ratio > 1.0: contrib = "🔥우수"
            if ratio > 3.0: contrib = "🚀떡상"

            perf = "🥉"
            if views > 10000: perf = "🥈"
            if views > 100000: perf = "🥇"

            data.append({
                "thumbnail": snip['thumbnails']['high']['url'],
                "title": snip['title'],
                "channel": snip['channelTitle'],
                "views": views,
                "subs": subs,
                "contrib": contrib,
                "perf": perf,
                "date": snip['publishedAt'][:10],
                "link": f"https://www.youtube.com/watch?v={item['id']}"
            })
        return data
    except: return []

st.title("🔎 YouTube 분석기 (Web Ver)")

c1, c2 = st.columns([4, 1])
with c1:
    keyword = st.text_input("검색어 입력", placeholder="주제 입력 (예: 탕후루)", label_visibility="collapsed")
with c2:
    search_btn = st.button("검색", type="primary")

if keyword or search_btn:
    if not keyword:
        st.warning("검색어를 입력해주세요.")
    else:
        with st.spinner("데이터 수집 중..."):
            raw_data = get_data(keyword)
            if raw_data:
                st.success(f"결과: {len(raw_data)}개")
                st.markdown("---")
                for item in raw_data:
                    with st.container():
                        col1, col2, col3 = st.columns([2, 5, 2])
                        col1.image(item['thumbnail'], use_container_width=True)
                        with col2:
                            st.subheader(item['title'])
                            st.caption(f"📺 {item['channel']} | 📅 {item['date']}")
                            st.write(f"[영상 보러가기]({item['link']})")
                        with col3:
                            st.metric("조회수", f"{item['views']:,}", item['perf'])
                            st.metric("구독자", f"{item['subs']:,}", item['contrib'])
                        st.divider()
            else:
                st.error("결과 없음")

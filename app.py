import streamlit as st
import pandas as pd
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import re

API_KEY = "AIzaSyCdvHrJntPbzY4A_-LD2byHikj2arwlgUc" 
st.set_page_config(page_title="Hiview Master", layout="wide")

if 'search_history' not in st.session_state:
    st.session_state['search_history'] = []
if 'saved_videos' not in st.session_state:
    st.session_state['saved_videos'] = pd.DataFrame()

st.markdown("""
    <style>
    .block-container { padding-top: 1rem; }
    .stDataFrame { border: 1px solid #eee; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

def parse_duration(duration):
    match = re.match(r'PT(\d+H)?(\d+M)?(\d+S)?', duration)
    if not match: return "00:00"
    h = int(match.group(1)[:-1]) if match.group(1) else 0
    m = int(match.group(2)[:-1]) if match.group(2) else 0
    s = int(match.group(3)[:-1]) if match.group(3) else 0
    if h > 0: return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def get_published_after(option):
    today = datetime.now()
    if option == "최근 1개월": date = today - timedelta(days=30)
    elif option == "최근 3개월": date = today - timedelta(days=90)
    elif option == "최근 1년": date = today - timedelta(days=365)
    else: return None
    return date.strftime("%Y-%m-%dT00:00:00Z")

@st.cache_data
def get_data(keyword, published_after, duration_mode):
    try:
        youtube = build('youtube', 'v3', developerKey=API_KEY)
        search_args = {'q': keyword, 'part': "id,snippet", 'maxResults': 50, 'type': "video", 'order': "viewCount"}
        
        if published_after: search_args['publishedAfter'] = published_after
        if duration_mode == "숏츠 (<4분)": search_args['videoDuration'] = 'short'
        elif duration_mode == "일반 (4~20분)": search_args['videoDuration'] = 'medium'
        elif duration_mode == "긴 영상 (>20분)": search_args['videoDuration'] = 'long'
        
        search = youtube.search().list(**search_args).execute()
        v_ids = [i['id']['videoId'] for i in search['items']]
        if not v_ids: return []
        
        videos = youtube.videos().list(part="snippet,statistics,contentDetails", id=','.join(v_ids)).execute()
        
        c_ids = list(set([i['snippet']['channelId'] for i in videos['items']]))
        c_stats = {}
        if c_ids:
            channels = youtube.channels().list(part="snippet,statistics,brandingSettings", id=','.join(c_ids[:50])).execute()
            for item in channels['items']:
                c_stats[item['id']] = {
                    'subs': int(item['statistics'].get('subscriberCount', 0)),
                    'keywords': item['brandingSettings'].get('channel', {}).get('keywords', '없음'),
                    'publishedAt': item['snippet'].get('publishedAt', '')[:10]
                }

        data = []
        for item in videos['items']:
            stat = item['statistics']
            snip = item['snippet']
            content = item['contentDetails']
            c_id = snip['channelId']
            
            views = int(stat.get('viewCount', 0))
            likes = int(stat.get('likeCount', 0))
            ch_info = c_stats.get(c_id, {})
            
            duration_str = parse_duration(content['duration'])
            is_shorts = "📺일반"
            if "H" not in content['duration']:
                if int(duration_str.split(':')[0]) < 1: is_shorts = "🩳숏츠"
                elif duration_mode == "숏츠 (<4분)": is_shorts = "🎞️짧은영상"

            eng_rate = ((likes) / views * 100) if views > 0 else 0
            
            data.append({
                "선택": False,
                "썸네일": snip['thumbnails']['default']['url'],
                "제목": snip['title'],
                "길이": duration_str,
                "유형": is_shorts,
                "조회수": views,
                "참여율": round(eng_rate, 2),
                "구독자": ch_info.get('subs', 0),
                "게시일": snip['publishedAt'][:10],
                "채널명": snip['channelTitle'],
                "채널키워드": ch_info.get('keywords', '')[:50],
                "링크": f"https://www.youtube.com/watch?v={item['id']}"
            })
        return data
    except Exception as e:
        return []

st.title("🚀 Hiview Master")

with st.sidebar:
    st.header("🗂️ 검색 기록")
    if st.session_state['search_history']:
        for h in reversed(st.session_state['search_history'][-5:]):
            if st.button(f"🕒 {h}", key=h): st.session_state['keyword_input'] = h
    
    st.divider()
    date_option = st.selectbox("📅 기간", ["최근 1개월", "최근 3개월", "최근 1년", "전체 기간"])
    duration_option = st.radio("⏳ 길이", ["모든 길이", "숏츠 (<4분)", "일반 (4~20분)", "긴 영상 (>20분)"])

tab1, tab2 = st.tabs(["🔍 분석", "⭐ 찜 목록"])

with tab1:
    c1, c2 = st.columns([5, 1])
    keyword = c1.text_input("검색어", key="keyword_input")
    run_btn = c2.button("분석 시작", type="primary", use_container_width=True)

    if run_btn and keyword:
        if keyword not in st.session_state['search_history']:
            st.session_state['search_history'].append(keyword)
        
        with st.spinner("데이터 수집 중..."):
            result = get_data(keyword, get_published_after(date_option), duration_option)
            if result:
                st.success(f"{len(result)}개 발견")
                edited_df = st.data_editor(
                    pd.DataFrame(result),
                    column_config={
                        "선택": st.column_config.CheckboxColumn("찜", default=False),
                        "썸네일": st.column_config.ImageColumn("이미지", width="small"),
                        "링크": st.column_config.LinkColumn("링크", display_text="보기"),
                        "참여율": st.column_config.NumberColumn("참여율", format="%.2f%%"),
                        "조회수": st.column_config.NumberColumn("조회수", format="%d회"),
                    },
                    hide_index=True, use_container_width=True, height=700
                )
                if not edited_df.empty:
                    saved = edited_df[edited_df['선택'] == True]
                    if not saved.empty:
                        st.session_state['saved_videos'] = pd.concat([st.session_state['saved_videos'], saved]).drop_duplicates(subset=['링크'])
                        st.toast("저장 완료!")
            else: st.error("결과 없음")

with tab2:
    if not st.session_state['saved_videos'].empty:
        save_df = st.session_state['saved_videos'].copy()
        if "선택" in save_df.columns: save_df = save_df.drop(columns=["선택"])
        st.dataframe(save_df, column_config={"썸네일": st.column_config.ImageColumn("이미지"), "링크": st.column_config.LinkColumn("링크")}, hide_index=True, use_container_width=True)
        st.download_button("💾 엑셀 다운로드", save_df.to_csv(index=False).encode('utf-8-sig'), "saved.csv", "text/csv")
        if st.button("🗑️ 전체 삭제"):
            st.session_state['saved_videos'] = pd.DataFrame()
            st.rerun()
    else: st.warning("찜한 영상이 없습니다.")

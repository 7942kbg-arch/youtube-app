import streamlit as st
import pandas as pd
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import re

# ==========================================
# [기본 설정] API 키
# ==========================================
API_KEY = "AIzaSyCdvHrJntPbzY4A_-LD2byHikj2arwlgUc" 
st.set_page_config(page_title="Hiview Master", layout="wide")

# 세션 상태 초기화
if 'search_history' not in st.session_state:
    st.session_state['search_history'] = []
if 'saved_videos' not in st.session_state:
    st.session_state['saved_videos'] = pd.DataFrame()

# 스타일 설정
st.markdown("""
    <style>
    .block-container { padding-top: 1rem; }
    .stDataFrame { border: 1px solid #eee; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# [함수] 영상 길이 변환 (PT1H2M10S -> 01:02:10)
def parse_duration(duration):
    match = re.match(r'PT(\d+H)?(\d+M)?(\d+S)?', duration)
    if not match: return "00:00"
    
    h = int(match.group(1)[:-1]) if match.group(1) else 0
    m = int(match.group(2)[:-1]) if match.group(2) else 0
    s = int(match.group(3)[:-1]) if match.group(3) else 0
    
    if h > 0: return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

# [함수] 날짜 계산
def get_published_after(option):
    today = datetime.now()
    if option == "최근 1개월": date = today - timedelta(days=30)
    elif option == "최근 3개월": date = today - timedelta(days=90)
    elif option == "최근 6개월": date = today - timedelta(days=180)
    elif option == "최근 1년": date = today - timedelta(days=365)
    else: return None
    return date.strftime("%Y-%m-%dT00:00:00Z")

# [핵심] 데이터 수집 함수
@st.cache_data
def get_data(keyword, published_after, duration_mode):
    try:
        youtube = build('youtube', 'v3', developerKey=API_KEY)
        
        # 1. 영상 검색 요청
        search_args = {
            'q': keyword, 
            'part': "id,snippet", 
            'maxResults': 50, 
            'type': "video", 
            'order': "viewCount"
        }
        
        if published_after: 
            search_args['publishedAfter'] = published_after
            
        if duration_mode == "숏츠 (<4분)":
            search_args['videoDuration'] = 'short'
        elif duration_mode == "일반 (4~20분)":
            search_args['videoDuration'] = 'medium'
        elif duration_mode == "긴 영상 (>20분)":
            search_args['videoDuration'] = 'long'
        
        search = youtube.search().list(**search_args).execute()
        v_ids = [i['id']['videoId'] for i in search['items']]
        if not v_ids: return []
        
        # 2. 상세 정보 요청
        videos = youtube.videos().list(
            part="snippet,statistics,contentDetails", 
            id=','.join(v_ids)
        ).execute()
        
        # 3. 채널 정보 요청
        c_ids = list(set([i['snippet']['channelId'] for i in videos['items']]))
        c_stats = {}
        if c_ids:
            channels = youtube.channels().list(
                part="snippet,statistics,brandingSettings", 
                id=','.join(c_ids[:50])
            ).execute()
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
            
            v

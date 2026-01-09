import streamlit as st
import pandas as pd
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import re

# ==========================================
# [기본 설정]
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

# [핵심] 데이터 수집 함수 (길이 필터 추가됨!)
@st.cache_data
def get_data(keyword, published_after, duration_mode):
    try:
        youtube = build('youtube', 'v3', developerKey=API_KEY)
        
        # 1. 영상 검색 (필터 적용)
        search_args = {
            'q': keyword, 
            'part': "id,snippet", 
            'maxResults': 50, 
            'type': "video", 
            'order': "viewCount"
        }
        
        # 날짜 필터
        if published_after: 
            search_args['publishedAfter'] = published_after
            
        # 길이 필터 (API 파라미터 매핑)
        if duration_mode == "숏츠 (<4분)":
            search_args['videoDuration'] = 'short'
        elif duration_mode == "일반 (4~20분)":
            search_args['videoDuration'] = 'medium'
        elif duration_mode == "긴 영상 (>20분)":
            search_args['videoDuration'] = 'long'
        
        search = youtube.search().list(**search_args).execute()
        v_ids = [i['id']['videoId'] for i in search['items']]
        if not v_ids: return []
        
        # 2. 영상 상세
        videos = youtube.videos().list(
            part="snippet,statistics,contentDetails", 
            id=','.join(v_ids)
        ).execute()
        
        # 3. 채널 상세
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
            
            v_tags = snip.get('tags', [])
            v_tag_str = ", ".join(v_tags[:5]) if v_tags else ""
            
            ch_info = c_stats.get(c_id, {})
            ch_subs = ch_info.get('subs', 0)
            ch_keywords = ch_info.get('keywords', '')
            if len(ch_keywords) > 50: ch_keywords = ch_keywords[:50] + "..."
            
            duration_str = parse_duration(content['duration'])
            
            # [유형 라벨링]
            # 1분 미만이고 숏츠 모드 검색이거나, 실제 길이가 짧으면 숏츠로 표시
            is_shorts = "📺일반"
            if "H" not in content['duration']: # 1시간 미만
                m_part = int(duration_str.split(':')[0])
                if m_part < 1: # 1분 미만
                    is_shorts = "🩳숏츠"
                elif duration_mode == "숏츠 (<4분)": # 사용자가 숏츠를 원했으면 4분 미만도 표시
                     is_shorts = "🎞️짧은영상"

            eng_rate = ((likes) / views * 100) if views > 0 else 0
            
            data.append({
                "선택": False,
                "썸네일": snip['thumbnails']['default']['url'],
                "제목": snip['title'],
                "길이": duration_str,
                "유형": is_shorts,
                "조회수": views,
                "참여율": round(eng_rate, 2),
                "구독자": ch_subs,
                "게시일": snip['publishedAt'][:10],
                "영상태그": v_tag_str,
                "채널명": snip['channelTitle'],
                "채널키워드": ch_keywords,
                "채널생성": ch_info.get('publishedAt', ''),
                "링크": f"https://www.youtube.com/watch?v={item['id']}"
            })
        return data
    except Exception as e:
        return []

# ==========================================
# [화면 구성]
# ==========================================
st.title("🚀 Hiview Master (Total Analysis)")

# 사이드바
with st.sidebar:
    st.header("🗂️ 검색 기록")
    if st.session_state['search_history']:
        for h in reversed(st.session_state['search_history'][-5:]):
            if st.button(f"🕒 {h}", key=h):
                st.session_state['keyword_input'] = h
    else:
        st.caption("기록 없음")
    
    st.divider()
    st.header("⚙️ 검색 필터")
    
    # [수정됨] 날짜와 길이를 한눈에 보기 좋게 배치
    date_option = st.selectbox(
        "📅 분석 기간", 
        ["최근 1개월", "최근 3개월", "최근 1년", "전체 기간"],
        index=0
    )
    
    duration_option = st.radio(
        "⏳ 영상 길이", 
        ["모든 길이", "숏츠 (<4분)", "일반 (4~20분)", "긴 영상 (>20분)"],
        index=0
    )
    st.caption("💡 '숏츠' 선택 시 API 기준 4분 미만 영상만 검색됩니다.")

# 메인 탭
tab1, tab2 = st.tabs(["🔍 키워드 분석", "⭐ 찜한 영상 리스트"])

with tab1:
    c1, c2 = st.columns(

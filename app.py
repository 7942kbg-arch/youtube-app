import streamlit as st
import pandas as pd
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import re

# ==========================================
# [설정] API 키
# ==========================================
API_KEY = "AIzaSyCdvHrJntPbzY4A_-LD2byHikj2arwlgUc"
st.set_page_config(page_title="Hiview Perfect", layout="wide")

# [세션 초기화] 검색 기록 저장용 (이게 있어야 기록이 남습니다)
if 'search_history' not in st.session_state:
    st.session_state['search_history'] = []

# 스타일 설정
st.markdown("""
    <style>
    .block-container { padding-top: 1rem; padding-bottom: 5rem; }
    </style>
""", unsafe_allow_html=True)

# [함수] 영상 길이 변환
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
    elif option == "최근 1년": date = today - timedelta(days=365)
    else: return None
    return date.strftime("%Y-%m-%dT00:00:00Z")

# [핵심] 데이터 수집
@st.cache_data
def get_data(keyword, published_after, duration_mode):
    try:
        youtube = build('youtube', 'v3', developerKey=API_KEY)
        
        # 1. 검색
        search_args = {
            'q': keyword, 'part': "id,snippet", 'maxResults': 50, 
            'type': "video", 'order': "viewCount"
        }
        if published_after: search_args['publishedAfter'] = published_after
        
        # 길이 필터
        if duration_mode == "숏츠 (<4분)": search_args['videoDuration'] = 'short'
        elif duration_mode == "일반 (4~20분)": search_args['videoDuration'] = 'medium'
        elif duration_mode == "긴 영상 (>20분)": search_args['videoDuration'] = 'long'
        
        search = youtube.search().list(**search_args).execute()
        v_ids = [i['id']['videoId'] for i in search['items']]
        if not v_ids: return []
        
        # 2. 상세 정보
        videos = youtube.videos().list(
            part="snippet,statistics,contentDetails", 
            id=','.join(v_ids)
        ).execute()
        
        # 3. 채널 정보
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
                    'videoCount': int(item['statistics'].get('videoCount', 0)),
                    'keywords': item['brandingSettings'].get('channel', {}).get('keywords', '없음')
                }

        data = []
        for item in videos['items']:
            stat = item['statistics']
            snip = item['snippet']
            content = item['contentDetails']
            c_id = snip['channelId']
            
            views = int(stat.get('viewCount', 0))
            likes = int(stat.get('likeCount', 0))
            comments = int(stat.get('commentCount', 0))
            
            ch_info = c_stats.get(c_id, {})
            subs = ch_info.get('subs', 0)
            total_videos = ch_info.get('videoCount', 0)
            ch_keywords = ch_info.get('keywords', '')
            if len(ch_keywords) > 50: ch_keywords = ch_keywords[:50] + "..."

            duration_str = parse_duration(content['duration'])
            
            is_shorts = "📺일반"
            if "H" not in content['duration']:
                if int(duration_str.split(':')[0]) < 1: is_shorts = "🩳숏츠"
                elif duration_mode == "숏츠 (<4분)": is_shorts = "🎞️짧은영상"

            eng_rate = ((likes + comments) / views * 100) if views > 0 else 0
            
            perf = "🥉"
            if views > 10000: perf = "🥈"
            if views > 100000: perf = "🥇"
            if views > 1000000: perf = "👑"
            
            ratio = (views / subs) if subs > 0 else 0
            contrib = "🌱"
            if ratio > 0.5: contrib = "🌿"
            if ratio > 1.0: contrib = "🔥"
            if ratio > 5.0: contrib = "🚀"

            data.append({
                "썸네일": snip['thumbnails']['medium']['url'],
                "제목": snip['title'],
                "길이": duration_str,
                "유형": is_shorts,
                "조회수": views,
                "실적": perf,
                "공헌": contrib,
                "참여율": round(eng_rate, 2),
                "좋아요": likes,
                "댓글": comments,
                "구독자": subs,
                "영상수": total_videos,
                "게시일": snip['publishedAt'][:10],
                "채널명": snip['channelTitle'],
                "채널키워드": ch_keywords,
                "링크": f"https://www.youtube.com/watch?v={item['id']}"
            })
        return data
    except Exception as e:
        return []

# ==========================================
# [화면 구성]
# ==========================================
st.title("📊 Hiview Analytics")

# [사이드바] 여기가 사진처럼 복구된 부분입니다!
with st.sidebar:
    st.header("📂 검색 기록")
    if st.session_state['search_history']:
        # 기록을 역순(최신순)으로 보여줌
        for h in reversed(st.session_state['search_history'][-5:]):
            if st.button(f"🕒 {h}", key=h, use_container_width=True):
                st.session_state['keyword_input'] = h
                st.rerun() # 버튼 누르면 바로 재실행
    else:
        st.caption("아직 기록이 없습니다.")
    
    st.divider()
    
    st.header("⚙️ 검색 옵션")
    date_option = st.selectbox("📅 분석 기간", ["최근 1개월", "최근 3개월", "최근 1년", "전체 기간"])
    duration_option = st.radio("⏳ 영상 길이", ["모든 길이", "숏츠 (<4분)", "일반 (4~20분)", "긴 영상 (>20분)"])

# [메인 검색창]
c1, c2 = st.columns([5, 1])
# key='keyword_input'을 줘서 사이드바 버튼과 연결함
keyword = c1.text_input("검색어 입력", placeholder="예: 숏폼 마케팅", key="keyword_input")
run_btn = c2.button("분석 시작", type="primary", use_container_width=True)

if run_btn and keyword:
    # 검색어 기록 저장
    if keyword not in st.session_state['search_history']:
        st.session_state['search_history'].append(keyword)
        
    pub_date = get_published_after(date_option)
    
    with st.spinner("데이터 분석 중..."):
        result = get_data(keyword, pub_date, duration_option)
        
        if result:
            st.success(f"'{keyword}' 결과: {len(result)}개 발견")
            df = pd.DataFrame(result)
            
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("💾 엑셀로 저장하기", csv, f"{keyword}_data.csv", "text/csv")

            st.dataframe(
                df,
                column_config={
                    "썸네일": st.column_config.ImageColumn("썸네일", width="medium"),
                    "제목": st.column_config.TextColumn("제목", width="large"),
                    "링크": st.column_config.LinkColumn("링크", display_text="보기"),
                    "조회수": st.column_config.NumberColumn("조회수", format="%d회"),
                    "좋아요": st.column_config.NumberColumn("좋아요", format="%d개"),
                    "댓글": st.column_config.NumberColumn("댓글", format="%d개"),
                    "구독자": st.column_config.NumberColumn("구독자", format="%d명"),
                    "영상수": st.column_config.NumberColumn("총 영상", format="%d개"),
                    "참여율": st.column_config.NumberColumn("참여율", format="%.2f%%"),
                    "실적": st.column_config.TextColumn("실적", help="조회수 등급"),
                    "공헌": st.column_config.TextColumn("공헌", help="구독자 대비 파급력"),
                    "채널키워드": st.column_config.TextColumn("채널 키워드", width="medium"),
                },
                hide_index=True,
                use_container_width=True,
                height=800
            )
        else:
            st.error("조건에 맞는 결과가 없습니다.")

import os, json, time
import streamlit as st

# 에이전트 모듈
from agents.news_crawler import NewsCrawlerAgent
from agents.news_ranker import NewsRankerAgent
from agents.news_analyst import NewsAnalystAgent
from agents.pdf_rag import ingest_pdfs, query_pdf_knowledge, collection  # collection.count() 사용
from agents.portfolio_agent import PortfolioAgent
from agents.orchestrator import OrchestratorAgent
from agents.econ_reporter import EconReporterAgent



st.set_page_config(page_title="경제 뉴스 에이전트 (All-in-One)", layout="wide")
st.title("🧠 경제 뉴스 에이전트 ")

# ---------------------------
# 사이드바: 설정
# ---------------------------
st.sidebar.header("⚙️ 설정")

# 뉴스 설정
news_count = st.sidebar.slider("뉴스 개수 (Top N)", min_value=3, max_value=15, value=6, step=1)
horizon_hours = st.sidebar.slider("최근 N시간 기사만 보기", min_value=6, max_value=48, value=18, step=3)

# 포트폴리오 설정 (portfolio.json 로드/저장)
st.sidebar.subheader("📦 내 포트폴리오")
default_tickers = ["AAPL", "TSLA", "MSFT"]
existing = default_tickers
if os.path.exists("portfolio.json"):
    try:
        with open("portfolio.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            existing = data.get("tickers", default_tickers)
    except Exception:
        existing = default_tickers
seed = ",".join(existing)
user_input = st.sidebar.text_input("종목 코드(콤마로 구분, 예: AAPL,TSLA,005930.KS)", seed)
if st.sidebar.button("포트폴리오 저장"):
    tickers = [t.strip() for t in user_input.split(",") if t.strip()]
    with open("portfolio.json", "w", encoding="utf-8") as f:
        json.dump({"tickers": tickers}, f, ensure_ascii=False, indent=2)
    st.sidebar.success("저장 완료! 페이지 새로고침(F5) 시 반영됩니다.")

# PDF RAG 인덱싱 실행
st.sidebar.subheader("📚 PDF RAG")
if st.sidebar.button("data/pdfs 폴더 인덱싱 실행"):
    with st.spinner("PDF 인덱싱 중... (용량/페이지 수에 따라 시간이 걸립니다)"):
        ingest_pdfs()
    st.sidebar.success("PDF 인덱싱 완료!")

# RAG 빠른 검색
quick_query = st.sidebar.text_input("RAG 빠른 검색 (예: 인플레이션)")
if st.sidebar.button("검색"):
    r = query_pdf_knowledge(quick_query, n_results=3)
    st.sidebar.write("검색 결과:")
    if not r:
        st.sidebar.info("관련 문서 없음")
    else:
        for i, item in enumerate(r, 1) if isinstance(r[0], dict) else enumerate(r, 1):
            if isinstance(item, dict):
                st.sidebar.markdown(f"**[{i}] {item.get('source','unknown')}**\n\n{item.get('content','')[:200]}…")
            else:
                st.sidebar.markdown(f"**[{i}]** {item[:200]}…")

# ---------------------------
# 탭 구성
# ---------------------------
tab_news, tab_rag, tab_port, tab_signal, tab_status = st.tabs(
    ["📰 뉴스/분석", "🔎 RAG 검색", "📈 포트폴리오", "🚀 종목 시그널", "🛠 상태/설정"]
)

# 전역 상태 캐시
if "latest_news" not in st.session_state:
    st.session_state.latest_news = []     # 크롤링 원본
if "ranked_news" not in st.session_state:
    st.session_state.ranked_news = []     # (score, article)
if "analyzed" not in st.session_state:
    st.session_state.analyzed = []        # 분석 결과 리스트

# ---------------------------
# 탭 1: 뉴스/분석
# ---------------------------
with tab_news:
    st.subheader("오늘의 뉴스/블로그 → 랭킹 → 분석(+RAG)")

    # 🔽 추가: 데이터 소스 선택
    mode = st.selectbox(
        "데이터 소스 선택",
        ["news", "blog", "both"],
        format_func=lambda x: {"news":"뉴스", "blog":"블로그", "both":"둘 다"}[x]
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        do_fetch = st.button("1) 뉴스/블로그 크롤링")
    with col2:
        do_analyze = st.button("2) 상위 N 분석 실행")
    with col3:
        do_run_all = st.button("🚀 전체 파이프라인 실행")

    # 🚀 전체 파이프라인 실행
    if do_run_all:
        tickers = [t.strip() for t in user_input.split(",") if t.strip()]
        orch = OrchestratorAgent(tickers=tickers, topk=news_count, horizon_hours=horizon_hours)
        with st.spinner(f"{mode} 파이프라인 실행 중..."):
            res = orch.run(source=mode)
        st.session_state.latest_news = res["articles"]
        st.session_state.ranked_news = res["ranked"]
        st.session_state.analyzed = res["analyzed"]
        st.session_state.portfolio_prices = res.get("portfolio_prices", {})
        st.success(f"✅ 완료! ({mode}) 수집 {len(res['articles'])}개 / 분석 {len(res['analyzed'])}건")

    # 1) 크롤링 + 랭킹 (기존 로직 유지)
    if do_fetch:
        with st.spinner("뉴스 크롤링 중..."):
            crawler = NewsCrawlerAgent(horizon_hours=horizon_hours)
            articles = crawler.collect_items()
            st.session_state.latest_news = articles
        st.success(f"크롤링 완료: 총 {len(st.session_state.latest_news)}개 기사")

        with st.spinner("랭킹/중복제거 중..."):
            ranker = NewsRankerAgent(topk=news_count)
            ranked = ranker.rank_items(st.session_state.latest_news)
            st.session_state.ranked_news = ranked
        st.info(f"상위 {len(st.session_state.ranked_news)}개 기사 선정")

    # 랭킹 미리보기 (기존)
    if st.session_state.ranked_news:
        st.markdown("**상위 기사 미리보기**")
        for i, (score, art) in enumerate(st.session_state.ranked_news, 1):
            with st.expander(f"[{i}] {art['title']}  ·  점수 {round(score,2)}  ·  {art['published']}"):
                st.markdown(f"- 링크: {art['link']}")
                st.markdown(f"- 요약(원문 제공): {art['summary'][:300]}…")

    # 2) Analyst(+RAG) 실행 (기존)
    if do_analyze:
        if not st.session_state.ranked_news:
            st.warning("먼저 '뉴스 크롤링'을 실행하세요.")
        else:
            st.session_state.analyzed = []
            analyst = NewsAnalystAgent()
            with st.spinner("Analyst가 상위 기사 분석 중..."):
                for _, art in st.session_state.ranked_news:
                    result = analyst.analyze(art)
                    st.session_state.analyzed.append({"article": art, "analysis": result})
            st.success("분석 완료!")

    # 분석 결과 표시 (기존)
    if st.session_state.analyzed:
        st.markdown("## 결과")
        for i, item in enumerate(st.session_state.analyzed, 1):
            art = item["article"]
            res = item["analysis"]
            with st.expander(f"{i}. {res.get('headline', art['title'])}  ·  {art['published']}"):
                st.write(f"[원문 보기]({art['link']})")
                st.markdown(f"**요약:** {res.get('summary','')}")
                st.markdown(f"**영향:** {res.get('impact','')}")
                kws = res.get("keywords", [])
                if kws:
                    st.markdown(f"**키워드:** {', '.join(kws)}")
                rag_ctx = res.get("rag_context", [])
                if rag_ctx:
                    st.markdown("**📚 추가 지식 (PDF RAG):**")
                    for ctx in rag_ctx:
                        st.markdown(f"- {ctx}")
        st.markdown("---")
        if st.button("📝 오늘 리포트(MD) 생성/저장"):
            rep = EconReporterAgent()
            md = rep.build_report(st.session_state.analyzed)
            path = rep.save_report(md)
            st.success(f"리포트 생성 완료: {path}")

            # 바로 화면에서 보기
            with st.expander("리포트 미리보기 (Markdown)"):
                st.markdown(md)
# ---------------------------
# 탭 2: RAG 검색 (인터랙티브)
# ---------------------------
with tab_rag:
    st.subheader("PDF RAG 검색")
    q = st.text_input("검색어를 입력하세요 (예: 인플레이션, 금리, GDP 등)", value=quick_query or "")
    nres = st.slider("검색 결과 개수", 1, 10, 3)
    if st.button("RAG 검색 실행"):
        if not q.strip():
            st.warning("검색어를 입력하세요.")
        else:
            with st.spinner("검색 중..."):
                r = query_pdf_knowledge(q.strip(), n_results=nres)
            if not r:
                st.info("관련 문서를 찾지 못했습니다.")
            else:
                st.success(f"총 {len(r)}건")
                # 결과 형태(구버전/신버전) 모두 대응
                for i, item in enumerate(r, 1):
                    if isinstance(item, dict):
                        st.markdown(f"**[{i}] 출처: {item.get('source','unknown')}**")
                        st.write(item.get("content","")[:800] + "…")
                    else:
                        st.markdown(f"**[{i}]**")
                        st.write(item[:800] + "…")

# ---------------------------
# 탭 3: 포트폴리오
# ---------------------------
with tab_port:
    st.subheader("내 포트폴리오 시세")
    tickers = [t.strip() for t in user_input.split(",") if t.strip()]
    pagent = PortfolioAgent(tickers=tickers)
    with st.spinner("시세 조회 중..."):
        prices = pagent.get_prices()
    if not prices:
        st.info("포트폴리오가 비어 있습니다.")
    else:
        rows = []
        for t, info in prices.items():
            ch = info.get("change")
            rows.append({
                "티커": t,
                "가격": info.get("price"),
                "변화율(%)": None if ch is None else round(float(ch), 2),
                "비고": info.get("note") or info.get("error")
            })
        st.dataframe(rows, use_container_width=True)

    # 뉴스와 연동 (현재 세션 분석 결과 기준)
    st.markdown("### 뉴스와 종목 매칭")
    if not st.session_state.analyzed:
        st.info("상단 '뉴스/분석' 탭에서 분석을 먼저 실행하면, 관련 종목 매칭을 보여줍니다.")
    else:
        linked_rows = []
        for item in st.session_state.analyzed:
            art = item["article"]
            txt = (art["title"] + " " + art["summary"]).lower()
            related = [t for t in tickers if t.lower() in txt]
            linked_rows.append({
                "제목": art["title"][:90] + ("…" if len(art["title"])>90 else ""),
                "링크": art["link"],
                "관련종목": ", ".join(related) if related else "-"
            })
        st.table(linked_rows)

# ---------------------------
# 탭 4: 상태/설정
# ---------------------------
with tab_status:
    st.subheader("상태/진단")
    # PDF DB 상태
    try:
        cnt = collection.count()
    except Exception:
        cnt = "N/A"
    st.write(f"PDF RAG chunks: **{cnt}**")

    # 환경 변수/모델
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY", "")
    model = os.getenv("MODEL", "gpt-4o-mini")
    st.write(f"OpenAI API Key 설정됨: **{'Yes' if api_key else 'No'}**")
    st.write(f"모델: **{model}**")

    st.caption("※ 투자 자문 아님. 데이터는 야후 파이낸스 무료 소스(지연 가능). PDF는 로컬 VectorDB(Chroma)에 저장되어 RAG로 검색됩니다.")

with tab_signal:
    st.subheader("🚀 오늘의 주목 종목")
    signals = st.session_state.get("signals", [])
    if not signals:
        st.info("아직 시그널 데이터가 없습니다. Orchestrator 전체 실행 후 확인하세요.")
    else:
        st.dataframe(signals)

with tab_signal:
    st.subheader("🚀 오늘의 주목 종목")
    signals = st.session_state.get("signals", [])
    if not signals:
        st.info("아직 시그널 데이터가 없습니다. Orchestrator 전체 실행 후 확인하세요.")
    else:
        st.dataframe(signals)

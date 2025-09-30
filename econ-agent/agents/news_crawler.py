import re
import hashlib
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import feedparser

# 설정
KST = ZoneInfo("Asia/Seoul")
FEEDS = [
    "https://feeds.reuters.com/reuters/businessNews",
    "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",  # WSJ Markets
    "https://www.ft.com/rss/home/asia",               # FT Asia
    "https://news.google.com/rss/search?q=%EA%B2%BD%EC%A0%9C&hl=ko&gl=KR&ceid=KR:ko"
]

# 중요 키워드 (가중치용)
KEYWORDS = [
    "금리", "물가", "환율", "실적", "수출", "반도체", "원유", "AI",
    "고용", "중국", "미국", "ECB", "FOMC", "CPI", "PPI", "GDP", "연준"
]

class NewsCrawlerAgent:
    def __init__(self, horizon_hours=18):
        """
        horizon_hours: 최근 몇 시간 이내의 뉴스를 가져올지 (기본 18시간)
        """
        self.horizon_hours = horizon_hours

    def collect_items(self):
        """RSS 피드에서 뉴스 기사 수집"""
        since = datetime.now(KST) - timedelta(hours=self.horizon_hours)
        items = []
        for url in FEEDS:
            feed = feedparser.parse(url)
            for e in feed.entries:
                # 발행 시간
                if hasattr(e, "published_parsed") and e.published_parsed:
                    pub = datetime(*e.published_parsed[:6], tzinfo=ZoneInfo("UTC")).astimezone(KST)
                else:
                    pub = datetime.now(KST)

                if pub < since:
                    continue

                title = e.title.strip()
                link = getattr(e, "link", "").strip()
                summary = re.sub(r"<[^>]+>", "", getattr(e, "summary", "")).strip()

                items.append({
                    "title": title,
                    "link": link,
                    "summary": summary,
                    "published": pub,
                    "source": url
                })
        return items

    def rank_items(self, items, topk=10):
        """키워드 매칭 + 최신성 기반 점수로 정렬"""
        seen = set()
        scored = []

        for it in items:
            # 중복 제거 (제목 기준)
            key = hashlib.md5(it["title"].lower().encode()).hexdigest()
            if key in seen:
                continue
            seen.add(key)

            # 키워드 매칭 점수
            txt = (it["title"] + " " + it["summary"]).lower()
            kw_score = sum(1 for kw in KEYWORDS if kw.lower() in txt) * 1.0

            # 최신성 가중치 (최근일수록 높음)
            hours_ago = (datetime.now(KST) - it["published"]).total_seconds() / 3600
            recency = max(0, 24 - hours_ago) * 0.3

            score = kw_score + recency
            scored.append((score, it))

        # 점수순 정렬
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:topk]


# 직접 실행할 때 테스트
if __name__ == "__main__":
    crawler = NewsCrawlerAgent()
    articles = crawler.collect_items()
    print(f"총 {len(articles)}개 기사 크롤링됨")

    ranked = crawler.rank_items(articles, topk=10)
    print("\n📌 상위 10개 기사:")
    for i, (score, art) in enumerate(ranked, 1):
        print(f"\n[{i}] 점수: {round(score,2)}")
        print("제목:", art["title"])
        print("링크:", art["link"])
        print("시간:", art["published"])
        print("요약:", art["summary"][:120], "...")

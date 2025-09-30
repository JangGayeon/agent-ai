import hashlib
from datetime import datetime
from zoneinfo import ZoneInfo
from agents.news_crawler import NewsCrawlerAgent

# 중요 키워드 (랭킹 점수 반영)
KEYWORDS = [
    "금리", "물가", "환율", "실적", "수출", "반도체", "원유", "AI",
    "고용", "중국", "미국", "ECB", "FOMC", "CPI", "PPI", "GDP", "연준"
]

KST = ZoneInfo("Asia/Seoul")

class NewsRankerAgent:
    def __init__(self, topk=10):
        self.topk = topk

    def rank_items(self, items):
        """뉴스 기사 리스트를 받아서 점수 매기고 상위 topk 반환"""
        seen = set()
        scored = []

        for it in items:
            # 중복 제거 (제목 해시 기준)
            key = hashlib.md5(it["title"].lower().encode()).hexdigest()
            if key in seen:
                continue
            seen.add(key)

            # 키워드 매칭 점수
            txt = (it["title"] + " " + it["summary"]).lower()
            kw_score = sum(1 for kw in KEYWORDS if kw.lower() in txt) * 1.0

            # 최신성 가중치 (최근 기사일수록 점수 ↑)
            hours_ago = (datetime.now(KST) - it["published"]).total_seconds() / 3600
            recency = max(0, 24 - hours_ago) * 0.3

            score = kw_score + recency
            scored.append((score, it))

        # 점수순 정렬 후 상위 topk 반환
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:self.topk]


# === 직접 실행 ===
if __name__ == "__main__":
    crawler = NewsCrawlerAgent()
    articles = crawler.collect_items()
    print(f"총 {len(articles)}개 기사 크롤링됨")

    ranker = NewsRankerAgent(topk=10)
    ranked = ranker.rank_items(articles)

    print("\n📌 상위 10개 기사:")
    for i, (score, art) in enumerate(ranked, 1):
        print(f"\n[{i}] 점수: {round(score,2)}")
        print("제목:", art["title"])
        print("링크:", art["link"])
        print("시간:", art["published"])
        print("요약:", art['summary'][:120], "...")
        print("출처:", art["source"])
        
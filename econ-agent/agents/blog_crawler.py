import feedparser
import datetime

class BlogCrawlerAgent:
    """
    경제/주식 관련 블로그/칼럼 RSS에서 글 수집
    """
    def __init__(self, horizon_days=3):
        self.horizon_days = horizon_days
        self.sources = [
            # 🔽 여기에 원하는 블로그/칼럼 RSS URL 추가
            # 네이버 블로그는 직접 RSS를 넣기 어렵고, 경제 전문 칼럼/매체 RSS를 넣는 게 안정적
            "https://seekingalpha.com/market_currents.xml",  # 시킹알파
            "https://www.kiplinger.com/feeds/rss.xml",      # Kiplinger (경제/투자)
            "https://rss.nytimes.com/services/xml/rss/nyt/Economy.xml", # NYT 경제 섹션
        ]

    def collect_items(self):
        """RSS 기반 블로그/칼럼 수집"""
        now = datetime.datetime.utcnow()
        horizon = now - datetime.timedelta(days=self.horizon_days)
        results = []

        for url in self.sources:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                # pubDate 가져오기
                published = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published = datetime.datetime(*entry.published_parsed[:6])
                else:
                    published = now

                if published < horizon:
                    continue

                item = {
                    "title": entry.get("title", ""),
                    "summary": entry.get("summary", ""),
                    "link": entry.get("link", ""),
                    "published": published.isoformat(),
                    "source": url
                }
                results.append(item)
        return results


if __name__ == "__main__":
    crawler = BlogCrawlerAgent(horizon_days=3)
    blogs = crawler.collect_items()
    print(f"총 {len(blogs)}개 블로그/칼럼 수집됨")
    for b in blogs[:5]:
        print(f"- {b['title']} ({b['published']})\n  {b['link']}")

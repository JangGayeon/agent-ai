from agents.news_crawler import NewsCrawlerAgent
from agents.blog_crawler import BlogCrawlerAgent
from agents.news_ranker import NewsRankerAgent
from agents.news_analyst import NewsAnalystAgent
from agents.portfolio_agent import PortfolioAgent
from agents.signal_agent import SignalAgent   # 👈 추가
from agents.econ_reporter import EconReporterAgent

class OrchestratorAgent:
    def __init__(self, tickers=None, topk=6, horizon_hours=18, horizon_days=3):
        self.tickers = tickers or []
        self.topk = topk
        self.horizon_hours = horizon_hours
        self.horizon_days = horizon_days

    def _collect(self, source: str):
        if source == "news":
            return NewsCrawlerAgent(self.horizon_hours).collect_items()
        elif source == "blog":
            return BlogCrawlerAgent(self.horizon_days).collect_items()
        elif source == "both":
            n = NewsCrawlerAgent(self.horizon_hours).collect_items()
            b = BlogCrawlerAgent(self.horizon_days).collect_items()
            return n + b
        else:
            raise ValueError("source must be 'news', 'blog' or 'both'")

    def run(self, source="news"):
        # 1) 수집
        articles = self._collect(source)

        # 2) 랭킹
        ranked = NewsRankerAgent(self.topk).rank_items(articles)

        # 3) 분석 (+RAG)
        analyst = NewsAnalystAgent()
        analyzed = [{"article": a, "analysis": analyst.analyze(a)} for _, a in ranked]

        # 4) 포트폴리오
        prices = PortfolioAgent(self.tickers).get_prices() if self.tickers else {}

        # 5) 시그널 (언급 빈도 + 시세 변동)
        signals = []
        if self.tickers:
            sig = SignalAgent(self.tickers)
            signals = sig.rank_signals(analyzed, prices)

        # 6) 리포트 작성
        reporter = EconReporterAgent()
        md = reporter.build_report(analyzed)
        if signals:
            md += "\n\n---\n\n## 🚀 오늘의 주목 종목\n"
            for s in signals[:5]:
                md += f"- **{s['ticker']}**: score={s['score']} / 언급 {s['mentions']}회 / 변화율 {s['change']}%\n"
        path = reporter.save_report(md)

        return {
            "source": source,
            "articles": articles,
            "ranked": ranked,
            "analyzed": analyzed,
            "portfolio_prices": prices,
            "signals": signals,
            "report_md": md,
            "report_path": path,
        }


if __name__ == "__main__":
    orch = OrchestratorAgent(
        tickers=["AAPL","TSLA","005930.KS"],
        topk=6,
        horizon_hours=18
    )
    res = orch.run(source="both")
    print("리포트 생성 완료:", res["report_path"])
    print("\n미리보기:\n", res["report_md"][:500])

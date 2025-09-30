import json, os
import pandas as pd
import yfinance as yf

class PortfolioAgent:
    def __init__(self, tickers=None, config_path="portfolio.json"):
        if tickers is not None:
            self.tickers = tickers
        else:
            self.tickers = self._load_from_file(config_path)

    def _load_from_file(self, path):
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("tickers", [])
        return []

    def get_prices(self):
        data = {}
        for t in self.tickers:
            try:
                stk = yf.Ticker(t)
                hist = stk.history(period="5d", auto_adjust=False).dropna(subset=["Close"])
                if hist.empty:
                    data[t] = {"price": None, "change": None, "error": "no data"}
                    continue
                df = hist.copy()
                df["DateOnly"] = pd.to_datetime(df.index).date
                last_by_day = df.groupby("DateOnly")["Close"].last()
                if len(last_by_day) >= 2:
                    prev_close = float(last_by_day.iloc[-2])
                    last_close = float(last_by_day.iloc[-1])
                    chg = (last_close/prev_close - 1.0) * 100.0 if prev_close else 0.0
                    data[t] = {"price": round(last_close, 2), "change": round(chg, 2)}
                else:
                    last_close = float(last_by_day.iloc[-1])
                    data[t] = {"price": round(last_close, 2), "change": None, "note": "only 1 day available"}
            except Exception as e:
                data[t] = {"price": None, "change": None, "error": str(e)}
        return data

    def link_with_news(self, news_list):
        """
        뉴스(랭킹 Agent 상위 기사)와 종목 키워드 매칭
        news_list: [{"title":..., "summary":...}, ...]
        """
        results = []
        for art in news_list:
            matched = [t for t in self.tickers if t.lower() in (art["title"]+art["summary"]).lower()]
            results.append({"article": art, "related": matched})
        return results


# === 직접 실행 ===
if __name__ == "__main__":
    # 관심 종목 예시
    my_stocks = ["AAPL", "TSLA", "MSFT"]

    agent = PortfolioAgent(my_stocks)

    # 주가 확인
    prices = agent.get_prices()
    print("📈 내 포트폴리오 시세:")
    for t, info in prices.items():
        print(f"- {t}: {info['price']} ({info['change']}%)")

    # 뉴스와 매칭 예시
    sample_news = [
        {"title": "Apple unveils new iPhone with AI features", "summary": "Analysts expect AAPL stock to rise."},
        {"title": "Tesla faces production delays in China", "summary": "TSLA might be affected by supply chain issues."},
    ]
    linked = agent.link_with_news(sample_news)

    print("\n📰 뉴스와 종목 매칭:")
    for item in linked:
        print(f"- 기사: {item['article']['title']}")
        if item["related"]:
            print(f"  관련 종목: {', '.join(item['related'])}")
        else:
            print("  관련 종목: 없음")

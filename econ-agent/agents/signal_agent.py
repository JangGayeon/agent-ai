# agents/signal_agent.py
import re
from collections import Counter

class SignalAgent:
    """
    뉴스/블로그 분석 결과 + 포트폴리오 시세를 종합해
    '주목할 종목' 순위를 도출하는 에이전트
    """
    def __init__(self, tickers=None):
        self.tickers = tickers or []

    def extract_mentions(self, analyzed):
        """분석 결과에서 종목 코드/회사명 언급 횟수 세기"""
        text_corpus = []
        for item in analyzed:
            a = item["analysis"]
            text_corpus.append(a.get("summary","") + " " + a.get("impact",""))
        full_text = " ".join(text_corpus).lower()

        counts = Counter()
        for t in self.tickers:
            if not t: continue
            # 단순히 ticker 문자열 기반 체크 (개선: 회사명 사전 매핑)
            pattern = r"\b" + re.escape(t.lower()) + r"\b"
            hits = len(re.findall(pattern, full_text))
            if hits > 0:
                counts[t] += hits
        return counts

    def rank_signals(self, analyzed, prices):
        """
        analyzed: [{"article":..,"analysis":{"summary","impact",..}}, ...]
        prices: {ticker: {"price":float,"change":float}}
        """
        mentions = self.extract_mentions(analyzed)
        results = []

        for t in self.tickers:
            info = prices.get(t, {})
            mention_count = mentions.get(t, 0)
            change = info.get("change", 0)
            score = mention_count*2 + (change or 0)  # 단순 가중치: 언급 2점 + %변화
            results.append({
                "ticker": t,
                "mentions": mention_count,
                "price": info.get("price"),
                "change": change,
                "score": round(score, 2),
            })
        # 점수순 정렬
        results.sort(key=lambda x: x["score"], reverse=True)
        return results


if __name__ == "__main__":
    from agents.portfolio_agent import PortfolioAgent

    # 데모용 입력
    fake_analyzed = [
        {"analysis": {"summary":"테슬라 자율주행 개선으로 투자 기대",
                      "impact":"TSLA에 긍정적 영향"}},
        {"analysis": {"summary":"애플 신제품 출시",
                      "impact":"AAPL 주가에 호재"}},
        {"analysis": {"summary":"삼성전자 메모리 업황 개선",
                      "impact":"005930.KS 전망 밝음"}},
    ]
    my_tickers = ["AAPL","TSLA","005930.KS"]
    prices = PortfolioAgent(my_tickers).get_prices()

    agent = SignalAgent(my_tickers)
    signals = agent.rank_signals(fake_analyzed, prices)

    print("🚀 주목 종목 순위")
    for s in signals:
        print(f"- {s['ticker']}: score={s['score']} / mentions={s['mentions']} / change={s['change']}%")

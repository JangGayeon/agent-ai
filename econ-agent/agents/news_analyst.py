import os, re, json
from dotenv import load_dotenv
from agents.pdf_rag import query_pdf_knowledge   # 🔥 PDF RAG 연결

# OpenAI SDK
use_llm = False
client = None
MODEL = "gpt-4o-mini"

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if OPENAI_API_KEY:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        use_llm = True
    except Exception:
        use_llm = False


class NewsAnalystAgent:
    def __init__(self, model=MODEL):
        self.model = model

    def analyze(self, article):
        """
        입력: {title, summary, link, published, source}
        출력: {"headline","summary","impact","keywords","rag_context"}
        """
        if not use_llm:
            return {
                "headline": article["title"],
                "summary": (article["summary"] or "기사 본문 없음")[:200],
                "impact": "LLM 비활성화 상태 (영향 분석 생략)",
                "keywords": [],
                "rag_context": []
            }

        prompt = f"""
역할: 경제/증시 전문 기자
기사 제목: {article['title']}
기사 요약(원문 제공): {article['summary']}

요청:
1) 한줄 핵심 요약 (<=20자, 한국어)
2) 기사 핵심 내용 요약 (3문장 이내)
3) 영향 분석: 거시/산업/종목에 어떤 메커니즘으로 영향을 줄지
4) 키워드 3개 (영문 약어 가능)

출력은 반드시 JSON만:
{{"headline":"","summary":"","impact":"","keywords":["","",""]}}
"""

        try:
            resp = client.chat.completions.create(
                model=self.model,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": "너는 경제 뉴스를 잘 요약하는 분석가야. JSON만 출력해."},
                    {"role": "user", "content": prompt}
                ]
            )
            content = resp.choices[0].message.content.strip()
            m = re.search(r"\{.*\}", content, re.S)
            data = json.loads(m.group(0)) if m else {}

            # 🔥 PDF RAG 지식 보강
            rag_context = []
            for kw in data.get("keywords", []):
                if kw:
                    docs = query_pdf_knowledge(kw, n_results=1)
                    if docs:
                        rag_context.append(f"{kw}: {docs[0]}")

            data["rag_context"] = rag_context
            return data

        except Exception as e:
            return {
                "headline": article["title"],
                "summary": (article["summary"] or "기사 본문 없음")[:200],
                "impact": f"분석 실패: {e}",
                "keywords": [],
                "rag_context": []
            }


# === 직접 실행 (테스트) ===
if __name__ == "__main__":
    from agents.news_crawler import NewsCrawlerAgent
    from agents.news_ranker import NewsRankerAgent

    crawler = NewsCrawlerAgent()
    articles = crawler.collect_items()
    print(f"총 {len(articles)}개 기사 크롤링됨")

    ranker = NewsRankerAgent(topk=3)
    ranked = ranker.rank_items(articles)

    analyst = NewsAnalystAgent()
    for score, art in ranked:
        result = analyst.analyze(art)
        print("\n----")
        print("제목:", result["headline"])
        print("요약:", result["summary"])
        print("영향:", result["impact"])
        print("키워드:", ", ".join(result["keywords"]))
        if result["rag_context"]:
            print("📚 추가 지식:")
            for ctx in result["rag_context"]:
                print("-", ctx)

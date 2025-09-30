# agents/econ_reporter.py
import os
import datetime as dt
from dotenv import load_dotenv

# LLM 사용 여부
use_llm, client = False, None
MODEL = os.getenv("MODEL", "gpt-4o-mini")

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_API_KEY:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        use_llm = True
    except Exception:
        use_llm = False


class EconReporterAgent:
    """
    입력: analyzed = [{"article": {...}, "analysis": {...}}, ...]
         각 analysis: {"headline","summary","impact","keywords","rag_context" (optional)}
    출력: Markdown 스트링 (일일 리포트)
    """
    def __init__(self, model: str = MODEL):
        self.model = model

    def _format_fallback(self, analyzed, date_str):
        # LLM이 없을 때의 단순 합성
        lines = [f"# 📊 일일 경제 리포트 — {date_str}", ""]
        if not analyzed:
            lines.append("_분석 결과가 없습니다._")
            return "\n".join(lines)

        # 섹션 구성: 주요 이슈 / 산업·테마 / 키워드 / PDF RAG 발췌
        lines += ["## 📰 주요 이슈 요약", ""]
        for i, item in enumerate(analyzed, 1):
            a = item["analysis"]
            art = item["article"]
            lines += [
                f"**{i}. {a.get('headline', art.get('title',''))}**",
                f"- 요약: {a.get('summary','(요약 없음)')}",
                f"- 영향: {a.get('impact','(영향 분석 없음)')}",
                f"- 링크: {art.get('link','')}",
                ""
            ]

        # 키워드 모아보기
        kwbag = []
        for item in analyzed:
            for kw in item["analysis"].get("keywords", []):
                if kw and kw not in kwbag:
                    kwbag.append(kw)
        if kwbag:
            lines += ["## 🔎 키워드", "", ", ".join(kwbag), ""]

        # RAG 컨텍스트 모음
        rag_lines = []
        for item in analyzed:
            for ctx in item["analysis"].get("rag_context", []):
                rag_lines.append(f"- {ctx[:300]}…")
        if rag_lines:
            lines += ["## 📚 PDF RAG 발췌", ""] + rag_lines + [""]

        # 간단 결론(휴리스틱)
        lines += [
            "## ✅ 오늘의 한 줄 결론",
            "- 거시: 금리·물가 관련 이슈가 시장 변동성을 좌우.",
            "- 산업/테마: 반도체·AI/에너지 기사 비중 확인.",
            "- 종목: 뉴스 언급·키워드 상위 종목 주목.",
            ""
        ]
        return "\n".join(lines)

    def _prompt(self, analyzed, date_str):
        # LLM용 프롬프트 생성
        bullets = []
        for item in analyzed:
            a = item["analysis"]; art = item["article"]
            bullets.append(
                f"- 제목: {a.get('headline', art.get('title',''))}\n"
                f"  요약: {a.get('summary','')}\n"
                f"  영향: {a.get('impact','')}\n"
                f"  키워드: {', '.join(a.get('keywords', []))}\n"
                f"  링크: {art.get('link','')}\n"
                f"  RAG: {' | '.join(a.get('rag_context', []))}\n"
            )
        body = "\n".join(bullets) if bullets else "(분석 없음)"

        return f"""
너는 경제 전문 에디터다. 아래 항목들을 종합해 **하루치 경제 리포트(Markdown)**를 작성하라.
형식은 반드시 섹션을 포함하라: 
# 제목, ## 주요 이슈, ## 산업·테마 포인트, ## 키워드, ## PDF RAG 발췌(있으면), ## 오늘의 한 줄 결론

- 날짜: {date_str}
- 톤: 간결/핵심 위주, 한국어, 과장 금지
- 불확실한 내용은 추정 표현 사용(예: 가능성, 관측)
- 표나 리스트를 적절히 활용

[분석 데이터]
{body}
"""

    def build_report(self, analyzed, date: dt.date | None = None) -> str:
        date_str = (date or dt.date.today()).isoformat()

        if use_llm and analyzed:
            try:
                resp = client.chat.completions.create(
                    model=self.model,
                    temperature=0.2,
                    messages=[
                        {"role": "system", "content": "You are a concise Korean economic editor who writes clean Markdown."},
                        {"role": "user", "content": self._prompt(analyzed, date_str)}
                    ],
                )
                md = resp.choices[0].message.content.strip()
                # 안전장치: 마크다운 헤더 없으면 붙이기
                if not md.lstrip().startswith("#"):
                    md = f"# 📊 일일 경제 리포트 — {date_str}\n\n" + md
                return md
            except Exception:
                pass  # LLM 실패 시 fallback

        return self._format_fallback(analyzed, date_str)

    def save_report(self, markdown: str, out_dir: str = "out", date: dt.date | None = None) -> str:
        os.makedirs(out_dir, exist_ok=True)
        date_str = (date or dt.date.today()).isoformat()
        path = os.path.join(out_dir, f"{date_str}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(markdown)
        return path


if __name__ == "__main__":
    # 간단 테스트 (빈 입력 시 폴백 마크다운)
    agent = EconReporterAgent()
    md = agent.build_report(analyzed=[])
    path = agent.save_report(md)
    print("리포트 생성:", path)

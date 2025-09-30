from agents.pdf_rag import query_pdf_knowledge, collection

def main():
    print(f"📚 현재 저장된 chunk 수: {collection.count()}")

    while True:
        query = input("\n🔎 검색할 키워드 입력 (종료하려면 'exit'): ").strip()
        if query.lower() in ["exit", "quit", "q"]:
            print("종료합니다 👋")
            break

        results = query_pdf_knowledge(query, n_results=3)

        if not results:
            print("❌ 관련 문서가 없습니다.")
        else:
            print(f"\n📚 '{query}' 관련 검색 결과:")
            for i, doc in enumerate(results, 1):
                print(f"[{i}] {doc[:200]}...\n")   # 그냥 내용만 출력


if __name__ == "__main__":
    main()

from agents.news_crawler import NewsCrawlerAgent

if __name__ == "__main__":
    crawler = NewsCrawlerAgent()
    articles = crawler.collect_items()

    print(f"총 {len(articles)}개 기사 수집됨")
    if articles:
        print("첫 번째 기사:", articles[0])

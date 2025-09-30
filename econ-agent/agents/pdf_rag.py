import os
import chromadb
from chromadb.utils import embedding_functions
import fitz  # PyMuPDF
from tqdm import tqdm

# 벡터DB 저장 경로
DB_DIR = "data/chroma"

embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

client = chromadb.PersistentClient(path=DB_DIR)
collection = client.get_or_create_collection(
    "pdf_knowledge",
    embedding_function=embedding_func
)


def extract_text_from_pdf(path: str) -> str:
    """PyMuPDF 기반 PDF 텍스트 추출 (진행률 표시)"""
    doc = fitz.open(path)
    text = ""
    for page in tqdm(doc, desc=f"읽는 중: {os.path.basename(path)}", unit="page"):
        text += page.get_text("text") + "\n"
    return text


def chunk_text(text: str, max_len: int = 800):
    """텍스트를 일정 길이 단위로 쪼개기"""
    chunks, current, length = [], [], 0
    for word in text.split():
        current.append(word)
        length += len(word) + 1
        if length >= max_len:
            chunks.append(" ".join(current))
            current, length = [], 0
    if current:
        chunks.append(" ".join(current))
    return chunks


def ingest_pdfs(pdf_dir="data/pdfs"):
    """PDF 폴더 안의 모든 파일을 읽어서 VectorDB에 저장"""
    if not os.path.exists(pdf_dir):
        print(f"[!] {pdf_dir} 폴더가 없습니다. 먼저 폴더를 만들어주세요.")
        return

    for fname in os.listdir(pdf_dir):
        if not fname.endswith(".pdf"):
            continue

        path = os.path.join(pdf_dir, fname)
        print(f"\n[+] {fname} 텍스트 추출 시작...")

        full_text = extract_text_from_pdf(path)
        chunks = chunk_text(full_text)

        if chunks:
            collection.add(
                documents=chunks,
                metadatas=[{"source": fname}] * len(chunks),
                ids=[f"{fname}_{i}" for i in range(len(chunks))]
            )
            print(f"[+] {fname} → {len(chunks)} chunks 저장 완료")
        else:
            print(f"[!] {fname} → 텍스트 추출 실패 (스캔본일 가능성)")


def query_pdf_knowledge(query_text, n_results=3):
    """PDF 지식 DB에서 관련 내용 검색"""
    result = collection.query(query_texts=[query_text], n_results=n_results)
    docs = result.get("documents", [[]])[0]
    return docs


def check_collection_stats():
    """현재 벡터DB에 몇 개의 문서가 저장됐는지 확인"""
    count = collection.count()
    print(f"📚 현재 저장된 chunk 수: {count}")
    return count


# === 직접 실행 ===
if __name__ == "__main__":
    ingest_pdfs()
    total = check_collection_stats()
    print("✅ PDF 인덱싱 완료!")
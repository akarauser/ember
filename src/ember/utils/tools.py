import hashlib
import os
import re
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.utils import model_downloader
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from rank_bm25 import BM25Plus
from sentence_transformers import SentenceTransformer

from ember.utils.logger import JsonLogger

logger = JsonLogger.setup_logger()

COLLECTION_NAME: str = "main"

CHROMA_DIR: Path = Path(__file__).parents[3] / "data/database"
EMBED_MODEL_PATH: Path = Path(__file__).parents[3] / "models/embed_model"
PDF_MODEL_PATH: Path = Path(__file__).parents[3] / "models/pdf_model"

CHROMA_DIR.mkdir(parents=True, exist_ok=True)
EMBED_MODEL_PATH.mkdir(parents=True, exist_ok=True)
PDF_MODEL_PATH.mkdir(parents=True, exist_ok=True)


if len(os.listdir(EMBED_MODEL_PATH)) == 0:
    embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    embedding_model.save_pretrained(str(EMBED_MODEL_PATH))
    logger.log(20, "Embedding model saved.")

if len(os.listdir(PDF_MODEL_PATH)) == 0:
    model_downloader.download_models(PDF_MODEL_PATH, progress=True)
    logger.log(20, "PDF model saved.")

EMBED_FUNCTION = HuggingFaceEmbeddings(model_name=str(EMBED_MODEL_PATH))

vector_store = Chroma(
    collection_name=COLLECTION_NAME,
    embedding_function=EMBED_FUNCTION,
    persist_directory=str(CHROMA_DIR),
)


def extract_filename_metadata(file_path: str) -> dict:
    """Extracts keywords from filename to be stored in database.

    Args:
        filepath(str): Path of file

    Returns:
        Dictionary of keywords
    """
    metadata = {}
    try:
        file_name = os.path.splitext(os.path.basename(file_path))[0]
        file_type = os.path.splitext(os.path.basename(file_path))[-1]
        filename_metadata = [
            word.strip().lower()
            for word in re.split(
                r"[-_ ]", os.path.splitext(os.path.basename(file_path))[0]
            )
            if word
        ]

        metadata["name"] = file_name
        metadata["type"] = file_type
        metadata["keywords"] = filename_metadata

        logger.log(
            20,
            f"Extracted keywords from {os.path.splitext(os.path.basename(file_path))[0]}.",
        )
    except Exception:
        logger.log(40, "File could not found.")

    return metadata


def create_file_hash(file_path: str) -> str:
    """Creates hash for the files.

    Args:
        filepath(str): Path of file

    Returns:
        Hash of file as string
    """
    hasher = hashlib.sha256()
    with open(file_path, "rb") as file:
        while chunk := file.read(4096):
            hasher.update(chunk)
    return hasher.hexdigest()


def extract_pages(file_path: str) -> list:
    """Extract pages from file and exports as Markdown type.

    Args:
        filepath(str): Path of file

    Returns:
        List of pages as string
    """
    try:
        pipeline_options = PdfPipelineOptions(artifacts_path=str(PDF_MODEL_PATH))
        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )
        result = converter.convert(file_path)
        page_break = "<!-- page break -->"
        markdown_text = result.document.export_to_markdown(
            page_break_placeholder=page_break
        )

        pages = markdown_text.split(page_break)
        logger.log(
            20,
            f"Extracted pages from {os.path.splitext(os.path.basename(file_path))[0]}.",
        )
        return pages
    except Exception:
        logger.log(40, "Failed to convert file.")
        return []


def ingest_document(file_path: str) -> None:
    """Ingests file if it has not been ingested before by checking the hash of the file.

    Args:
        filepath(str): Path of file
    """
    file_hash = create_file_hash(file_path)
    file_metadata = extract_filename_metadata(file_path)

    existing = vector_store.get(
        where={"file_hash": file_hash},
        include=["metadatas"],
    )
    if existing["metadatas"]:
        logger.log(20, f"{file_metadata['name']} already ingested.")
        return

    pages = extract_pages(file_path)

    batch_size = 16
    docs_batch: list[Document] = []

    for page, page_content in enumerate(pages, start=1):
        metadata_dict = file_metadata.copy()
        metadata_dict["page"] = page
        metadata_dict["file_hash"] = file_hash

        doc = Document(page_content=page_content, metadata=metadata_dict)
        docs_batch.append(doc)

        if len(docs_batch) >= batch_size:
            vector_store.add_documents(docs_batch)
            logger.log(20, "Batch ingested.")
            docs_batch = []

    if docs_batch:
        vector_store.add_documents(docs_batch)
    logger.log(20, "Ingestion completed.")


def search_docs(query: str, filter: str | None = None, k: int = 5) -> list[Document]:
    """Retrieves the documents from vector store.

    Args:
        query(str): Searching query
        k(int): Number of retrieved documents
    """
    if filter:
        retriever = vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": k,
                "fetch_k": k * 20,
                "filter": {"keywords": {"$contains": filter}},
            },
        )
        return retriever.invoke(query)

    retriever = vector_store.as_retriever(
        search_type="mmr", search_kwargs={"k": k, "fetch_k": k * 20}
    )

    return retriever.invoke(query)


def extract_headings_with_content(text):
    """
    Extract markdown headings with one paragraph of content after them.

    Args:
        text: Document text content

    Returns:
        List of extracted heading + content chunks
    """

    chunks = []
    sections = text.split("\n\n")
    i = 0

    while i < len(sections):
        section = sections[i].strip()
        pattern = r"^#+\s+"
        if re.match(pattern, section):
            heading = section
            if i + 1 < len(sections):
                next_content = sections[i + 1].strip()
                chunk = f"{heading}\n\n{next_content}"
                i = i + 2
            else:
                chunk = heading
                i = i + 1
            chunks.append(chunk)
        else:
            i = i + 1

    return chunks


def rank_documents_by_query(query: str, docs: list[Document], k=5) -> list[Document]:
    """
    Rank documents using BM25Plus on heading+content chunks.

    Args:
        docs: List of Document objects to rank
        keywords: List of keywords to rank by
        k: Number of top documents to return

    Returns:
        List of top-k Document objects sorted by BM25 score
    """

    if not docs:
        logger.log(20, "Either No doc or keywords found!")
        return docs

    query_tokens = query.lower().split(" ")

    doc_chunks = []
    for doc in docs:
        chunks = extract_headings_with_content(doc.page_content)
        combined = " ".join(chunks) if chunks else doc.page_content
        doc_chunks.append(combined.lower().split(" "))

    # doc_chunks = [doc.page_content.split(" ") for doc in docs]

    if not doc_chunks:
        logger.log(40, "Failed to create chunks.")

    bm25 = BM25Plus(doc_chunks)
    doc_scores = bm25.get_scores(query_tokens)

    ranked_indices = sorted(
        range(len(doc_scores)), key=lambda i: doc_scores[i], reverse=True
    )

    for rank, idx in enumerate(ranked_indices[:k], 1):
        logger.log(20, f"[{rank}] Doc {idx}: score={doc_scores[idx]:.4f}")

    return [docs[i] for i in ranked_indices[:k]]


def retrieve_results(query: str, filter: str | None = None, k: int = 10):
    """Main function to retrieve and return documents."""
    if filter:
        docs = search_docs(query, filter, k)
        logger.log(20, f"Retrieved with {filter} filter.")
    else:
        docs = search_docs(query, k=k)
        logger.log(20, "Retrieved without filter.")

    try:
        docs_ranked = rank_documents_by_query(query, docs, k)
    except Exception:
        logger.log(40, "Failed to initiate rankings.")
        docs_ranked = docs

    if len(docs) == 0:
        return f"No document found for the query: '{query}'."

    retrieved_text = []
    for i, doc in enumerate(docs_ranked, 1):
        doc_text = [f"\n# DOCUMENT {i}\n---"]

        for key, value in sorted(doc.metadata.items()):
            doc_text.append(f"- {key}: {value}")

        doc_text.append(f"\n{doc.page_content}")

        text = "\n".join(doc_text)
        retrieved_text.append(text)

    retrieved_text = "\n".join(retrieved_text)
    return retrieved_text

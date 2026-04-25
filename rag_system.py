import os
import time
from typing import List, Dict, Any, TypedDict
from dotenv import load_dotenv
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_community.vectorstores import Chroma
from duckduckgo_search import DDGS
from scrapling import StealthyFetcher
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from observability import setup_observability, estimate_cost, count_tokens, flush_traces

# Load environment variables
load_dotenv()

# Initialize Observability
ENABLE_PHOENIX = os.getenv("ENABLE_PHOENIX", "true").lower() == "true"
session = setup_observability() if ENABLE_PHOENIX else None

# Initialize Embeddings and LLM
embeddings = OllamaEmbeddings(model="llama3.2")
llm = ChatOllama(model="llama3.2", temperature=0)

# Vector Store Setup
PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
vector_store = Chroma(
    collection_name="rag_collection",
    embedding_function=embeddings,
    persist_directory=PERSIST_DIR
)

# Seed sample data if empty
def seed_data():
    if len(vector_store.get()["ids"]) == 0:
        print("---SEEDING DATA---")
        texts = [
            "LangGraph is a library for building stateful, multi-actor applications with LLMs.",
            "ChromaDB is an open-source embedding database for AI applications.",
            "Arize Phoenix is a tool for observability and evaluation of LLM applications.",
            "RAGAS is a framework for evaluating Retrieval Augmented Generation systems.",
            "Llama 3.2 is a state-of-the-art open source large language model from Meta."
        ]
        vector_store.add_texts(texts)

# State Definition
class GraphState(TypedDict):
    question: str
    context: List[str]
    answer: str
    ttft: float
    cost: float
    precision_score: float
    use_web: bool # Flag to trigger web search if local docs are poor

# Nodes
def retrieve(state: GraphState):
    print("---RETRIEVING---")
    question = state["question"]
    docs = vector_store.similarity_search(question, k=3)
    context = [doc.page_content for doc in docs]
    return {"context": context, "use_web": False}

def grade_documents(state: GraphState):
    """
    Determines whether the retrieved documents are relevant to the question.
    """
    print("---CHECKING RELEVANCE---")
    question = state["question"]
    documents = state["context"]
    
    class Grade(BaseModel):
        """Binary score for relevance check."""
        binary_score: str = Field(description="Relevance score 'yes' or 'no'")

    try:
        structured_llm = llm.with_structured_output(Grade)
        prompt = ChatPromptTemplate.from_template("""
        You are a grader assessing relevance of a retrieved document to a user question. 
        If the document contains keyword(s) or semantic meaning related to the user question, grade it as relevant. 
        Retrieved Documents: {documents}
        User Question: {question}
        Give a binary score 'yes' or 'no' to indicate whether the document is relevant to the question.
        """)
        grader_chain = prompt | structured_llm
        score = grader_chain.invoke({"question": question, "documents": " ".join(documents)})
        binary_score = score.binary_score.lower()
    except Exception as e:
        print(f"Structured output failed, falling back to manual parsing: {e}")
        prompt = ChatPromptTemplate.from_template("""
        Is the following document relevant to the user question? 
        Answer only with 'yes' or 'no'.
        Document: {documents}
        Question: {question}
        """)
        grader_chain = prompt | llm
        response = grader_chain.invoke({"question": question, "documents": " ".join(documents)})
        binary_score = "yes" if "yes" in response.content.lower() else "no"
    
    if binary_score == "yes":
        print("---DECISION: DOCUMENTS RELEVANT---")
        return {"use_web": False}
    else:
        print("---DECISION: DOCUMENTS NOT RELEVANT, TRIGGERING WEB SEARCH---")
        return {"use_web": True}

def web_search(state: GraphState):
    """
    Search DuckDuckGo for top URLs and scrape their contents using Scrapling.
    """
    print("---SEARCHING & SCRAPING THE WEB (FREE)---")
    question = state["question"]
    
    # 1. Search for URLs
    results = []
    try:
        with DDGS() as ddgs:
            ddg_gen = ddgs.text(question, max_results=3)
            for r in ddg_gen:
                results.append(r['href'])
    except Exception as e:
        print(f"DDG Search failed: {e}")
        return {"context": state["context"]}

    # 2. Scrape contents
    web_results = []
    for url in results:
        print(f"Scraping: {url}...")
        try:
            page = StealthyFetcher.fetch(url, headless=True, timeout=15000)
            # Simple text extraction from the first few paragraphs/sentences
            text = page.get_all_text()
            # Truncate content to keep it manageable for the LLM
            truncated_text = text[:1500] + "..." if len(text) > 1500 else text
            web_results.append(truncated_text)
        except Exception as e:
            print(f"Scraping {url} failed: {e}")
            continue
    
    print(f"Successfully scraped {len(web_results)} web sources.")
    return {"context": state["context"] + web_results}

def generate(state: GraphState):
    print("---GENERATING---")
    question = state["question"]
    context = state["context"]
    
    prompt = ChatPromptTemplate.from_template("""
    You are a helpful assistant. Use the following context to answer the question.
    If the context is empty or irrelevant, just say you don't know based on the context.
    
    Context: {context}
    Question: {question}
    Answer:
    """)
    
    start_time = time.time()
    ttft = 0
    full_response = ""
    
    # Measure TTFT (Time To First Token)
    # format prompt properly
    formatted_prompt = prompt.format(context=" ".join(context), question=question)
    for chunk in llm.stream(formatted_prompt):
        if ttft == 0:
            ttft = time.time() - start_time
        full_response += chunk.content
        
    return {"answer": full_response, "ttft": ttft}

def collector(state: GraphState):
    print("---COLLECTING METRICS---")
    question = state["question"]
    context = state["context"]
    answer = state["answer"]
    
    # Calculate Cost
    input_text = f"{question} {' '.join(context)}"
    input_tokens = count_tokens(input_text)
    output_tokens = count_tokens(answer)
    cost = estimate_cost(input_tokens, output_tokens)
    
    # Simple Precision Score (Demonstration)
    keywords = set(" ".join(context).lower().split())
    answer_words = set(answer.lower().split())
    if keywords:
        precision = len(keywords.intersection(answer_words)) / len(keywords)
    else:
        precision = 0.0
        
    print(f"TTFT: {state['ttft']:.4f}s")
    print(f"Estimated Cost: ${cost:.6f}")
    print(f"Precision Score (Simulated): {precision:.4f}")
    
    return {"cost": cost, "precision_score": precision}

# Build Graph
builder = StateGraph(GraphState)
builder.add_node("retrieve", retrieve)
builder.add_node("grade_documents", grade_documents)
builder.add_node("web_search", web_search)
builder.add_node("generate", generate)
builder.add_node("collector", collector)

builder.set_entry_point("retrieve")
builder.add_edge("retrieve", "grade_documents")

# Binary routing
def route_after_grading(state: GraphState):
    if state["use_web"]:
        return "web_search"
    else:
        return "generate"

builder.add_conditional_edges(
    "grade_documents",
    route_after_grading,
    {
        "web_search": "web_search",
        "generate": "generate"
    }
)

builder.add_edge("web_search", "generate")
builder.add_edge("generate", "collector")
builder.add_edge("collector", END)

rag_app = builder.compile()

if __name__ == "__main__":
    seed_data()
    example_input = {"question": "What is the latest score of the most recent cricket match?"}
    result = rag_app.invoke(example_input)
    print("\n---FINAL RESULT---")
    print(f"Answer: {result['answer']}")
    print(f"Metrics: TTFT={result['ttft']:.4f}s, Cost=${result['cost']:.6f}")
    
    # Keep session alive for a bit to view dashboard
    flush_traces()
    if session:
        print(f"\n🚀 Phoenix Dashboard available at: {session.url}")
        print("Traces are being sent... Keep this script running to view the dashboard.")
        print("Waiting for 120 seconds for you to inspect... (Press Ctrl+C to stop)")
        try:
            time.sleep(120)
        except KeyboardInterrupt:
            print("\nStopped.")
    else:
        print("\nPhoenix Dashboard could not be launched locally.")
        print("However, instrumentation is active. If a dashboard is already running at http://localhost:6006, please check it now.")
        print("Waiting for 5 seconds for traces to flush...")
        try:
            time.sleep(5)
        except KeyboardInterrupt:
            print("\nStopped.")

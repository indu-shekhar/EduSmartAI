"""
Simple command-line QA using Gemini LLM API (no RAG, no vector store).
Set GEMINI_API_KEY as an environment variable or edit below.
"""
import os
import sys
from llama_index.llms.gemini import Gemini

def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: Please set the GEMINI_API_KEY environment variable.")
        sys.exit(1)

    llm = Gemini(
        model_name="models/gemini-2.5-flash",
        api_key=api_key,
        temperature=0.7,
        max_tokens=1024
    )

    print("Simple Gemini QA (no RAG, no vector store)")
    print("Type your question and press Enter. Type 'exit' to quit.\n")
    while True:
        question = input("Q: ").strip()
        if question.lower() in {"exit", "quit"}:
            print("Goodbye!")
            break
        if not question:
            continue
        try:
            answer = llm.complete(question)
            print(f"A: {answer}\n")
        except Exception as e:
            print(f"Error: {e}\n")

if __name__ == "__main__":
    main()

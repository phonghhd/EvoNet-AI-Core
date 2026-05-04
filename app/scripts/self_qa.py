import os
import sys
import datetime
from dotenv import load_dotenv

load_dotenv("/app/.env", override=True)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'utils'))
from ai_failover import ask_ai, get_embedding, send_telegram


def generate_qa():
    send_telegram("Synthetic QA: generating attack scenario...")

    prompt = """Create a realistic cyberattack scenario including:
1. Vulnerability description
2. Exploitation method
3. Defense strategy

Reply in professional Vietnamese. Use <code> tags for technical parts."""

    try:
        qa_content, model = ask_ai(prompt)

        vector_data = get_embedding(qa_content)
        if vector_data:
            from pinecone import Pinecone
            pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
            memory_index = pc.Index("evonet-memory")

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            doc_id = f"dream_qa_{timestamp}"

            memory_index.upsert(
                vectors=[{
                    "id": doc_id,
                    "values": vector_data,
                    "metadata": {
                        "source": "self_generated_dream",
                        "type": "qa_simulation",
                        "model": model,
                        "text": qa_content
                    }
                }],
                namespace="learned_skills"
            )
            preview = qa_content[:300].replace('<', '<').replace('>', '>')
            send_telegram(f"Generated QA scenario using {model}\n{preview}...")
            print(f"QA generated using {model}")
    except Exception as e:
        send_telegram(f"QA generation failed: {e}")
        print(f"Error: {e}")


if __name__ == "__main__":
    generate_qa()

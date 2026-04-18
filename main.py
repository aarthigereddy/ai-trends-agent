import feedparser
import os
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime
import smtplib
from email.mime.text import MIMEText

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

FEEDS = [
    # Research
    "https://openai.com/blog/rss.xml",
    "https://www.anthropic.com/news/rss.xml",
    "https://deepmind.google/blog/rss.xml",
    "https://huggingface.co/blog/feed.xml",

    # Engineering / Tools
    "https://blog.langchain.dev/rss/",

    # News / Curated
    "https://www.technologyreview.com/feed/",
    "https://www.deeplearning.ai/the-batch/feed/",
    "https://hnrss.org/frontpage",
    "http://export.arxiv.org/rss/cs.AI",
    "http://export.arxiv.org/rss/cs.CL",
    "https://www.bloomberg.com/feed/podcast/etf-report.xml",
    "https://www.theverge.com/rss/index.xml"
]

def fetch_articles():
    articles = []
    seen_titles = set()

keywords = [
    "ai", "model", "llm", "rag", "agent", "agents",
    "openai", "anthropic", "claude", "gemini",
    "google", "deepmind", "mcp", "tool use",
    "fine-tune", "reasoning", "inference"
]
    for url in FEEDS:
        print(f"Fetching from: {url}")

        feed = feedparser.parse(url)

        for entry in feed.entries[:10]:
            title = entry.title.strip()
            summary = entry.get("summary", "")

            # Dedup
            if title in seen_titles:
                continue
            seen_titles.add(title)

            # Filter
            if not any(k in title.lower() or k in summary.lower() for k in keywords):
                continue

            articles.append({
                "title": title,
                "summary": summary
            })

    return articles


def summarize(articles):
    text = "\n\n".join([
        f"Title: {a['title']}\nSummary: {a['summary']}"
        for a in articles
    ])

    prompt = f"""
You are a senior AI analyst and career advisor.

Analyze the following AI news and produce a concise daily briefing.

STRICT RULES:
- Only use information explicitly present in the input
- Do NOT invent model names, versions, or products
- Avoid vague or generic statements
-Only include the most impactful developments for AI engineers and product builders.
-ONLY use names explicitly present in the input text. Do not infer future model versions or speculate.
Structure your output EXACTLY like this:
-ONLY use tools, models, companies, and products explicitly mentioned in the input text.
Do NOT infer or generate any model names, versions, or product names.
If not present, omit them.
🧠 AI Trends (include all relevant points)

🚀 New Tools / Products (only if clearly mentioned)

📊 What This Means (VERY IMPORTANT)
- Focus on skills/tools to learn
- Keep it practical

⚠️ Noise to Ignore (optional)

Keep it sharp, short, and actionable.

Content:
{text}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    return response.choices[0].message.content


def send_email(summary):
    sender = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")
    receiver = sender  # send to yourself

    msg = MIMEText(summary)
    msg["Subject"] = "🧠 Daily AI Trends Brief"
    msg["From"] = sender
    msg["To"] = receiver

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.send_message(msg)

        print("✅ Email sent successfully!")

    except Exception as e:
        print("❌ Error sending email:", e)


# ================= MAIN EXECUTION =================

articles = fetch_articles()

summary = summarize(articles)

today = datetime.now().strftime("%B %d")
header = f"Good morning Aarthi ☀️\n\n📅 {today}\n\n"

final_output = header + summary

print("\n🧠 AI TRENDS BRIEF:\n")
print(final_output)

send_email(final_output)
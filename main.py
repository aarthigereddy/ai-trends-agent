import os
import feedparser
import smtplib
import re

from dotenv import load_dotenv
from datetime import datetime
from email.mime.text import MIMEText

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

# ================= LOAD ENV =================

load_dotenv()

# ================= RSS FEEDS =================

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
    "https://www.theverge.com/rss/index.xml"
]

# ================= BASIC KEYWORDS =================

KEYWORDS = [
    "ai", "model", "llm", "rag", "agent", "agents",
    "openai", "anthropic", "claude", "gemini",
    "google", "deepmind", "mcp", "tool use",
    "fine-tune", "reasoning", "inference"
]

# ================= LLM =================

llm = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0.3
)

# ================= SCORING CHAIN =================

score_prompt = ChatPromptTemplate.from_template("""
You are an AI engineering news evaluator.

Evaluate how important this article is for:
- AI engineers
- GenAI developers
- LLM application builders

ARTICLE:
{article}

Return ONLY:

Score: <1-10>

Reason: <short reason>
""")

score_chain = score_prompt | llm

# ================= SUMMARY CHAIN =================

summary_prompt = ChatPromptTemplate.from_template("""
You are a senior AI analyst and career advisor.

Analyze the following AI news and produce a concise daily briefing.

STRICT RULES:
- Only use information explicitly present
- Do NOT invent products or model names
- Focus on practical impact for AI engineers
- Keep it concise and actionable

Structure EXACTLY like this:

🧠 AI Trends

🚀 New Tools / Products

📊 What This Means
- practical takeaways
- skills/tools to learn

⚠️ Noise to Ignore (optional)

CONTENT:
{text}
""")

summary_chain = summary_prompt | llm

# ================= ARTICLE SCORING =================

def score_article(article):

    text = f"""
Title: {article['title']}

Summary:
{article['summary']}
"""

    result = score_chain.invoke({
        "article": text
    })

    return result.content

# ================= FETCH ARTICLES =================

def fetch_articles():

    articles = []
    seen_links = set()
    for url in FEEDS:

        print(f"\nFetching from: {url}")

        feed = feedparser.parse(url)

        for entry in feed.entries[:10]:

            title = entry.title.strip()
            summary = entry.get("summary", "")
            link = entry.link
            # Deduplicate
            if link in seen_links:
                continue

            seen_links.add(link)

            # Basic keyword filtering
            if not any(
                k in title.lower() or k in summary.lower()
                for k in KEYWORDS
            ):
                continue

            article = {
                "title": title,
                "summary": summary,
                "link": entry.link,
                "source": feed.feed.get("title", "Unknown")

            }
            try:
                # AI relevance scoring
                score_result = score_article(article)
                match = re.search(r"Score:\s*(\d+)", score_result)
                if match:
                    score = int(match.group(1))
                    if score >= 7: 
                        articles.append(article)
                else:
                    print(f"No score found for article {title}")
            except Exception as e:
                print(f"Error scoring article {title}: {e}")
                print(e)
    return articles[:20]
# ================= SUMMARIZATION =================

def summarize_articles(articles):

    text = "\n\n".join([
        f"Title: {a['title']}\nSummary: {a['summary']}"
        for a in articles
    ])

    result = summary_chain.invoke({
        "text": text
    })

    return result.content

# ================= EMAIL =================

def send_email(summary):

    sender = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")

    receiver = sender

    msg = MIMEText(summary)

    msg["Subject"] = "🧠 Daily AI Trends Brief"
    msg["From"] = sender
    msg["To"] = receiver

    try:

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:

            server.login(sender, password)
            server.send_message(msg)

        print("\n✅ Email sent successfully!")

    except Exception as e:

        print("\n❌ Error sending email:")
        print(e)

# ================= MAIN EXECUTION =================

articles = fetch_articles()

print(f"\n✅ Selected {len(articles)} high-quality articles")

summary = summarize_articles(articles)

today = datetime.now().strftime("%B %d")

header = f"""
Good morning Aarthi ☀️

📅 {today}

"""

final_output = header + summary

print("\n================ AI TRENDS BRIEF ================\n")

print(final_output)

send_email(final_output)
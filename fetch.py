
import feedparser
import time
import requests
import re
from bs4 import BeautifulSoup
from langdetect import detect
from typing import Optional, List, Dict, Set

TOKEN = '7853715186:AAEQ0UoMHrQFUu3owEXvctUTOxBPS0mBMwI'
CHANNEL_HANDLE = '@CryptoNewsForFriends'
CRYPTO_PANIC_TOKEN = 'b19be245cfb69c6b5ea3a6699bb59fadb07bd5c2'

CURRENCY_KEYWORDS: Dict[str, List[str]] = {
    'BTC': ['bitcoin', 'btc'],
    'ETH': ['ethereum', 'eth'],
    'BNB': ['bnb'],
    'XRP': ['xrp', 'ripple'],
    'ADA': ['cardano', 'ada'],
    'DOGE': ['dogecoin', 'doge'],
    'SOL': ['solana', 'sol'],
    'USDT': ['tether', 'usdt'],
    'DOT': ['polkadot', 'dot'],
    'AVAX': ['avalanche', 'avax'],
    'LINK': ['chainlink', 'link'],
    'LTC': ['litecoin', 'ltc'],
    'TRX': ['tron', 'trx'],
    'MATIC': ['polygon', 'matic'],
    'UNI': ['uniswap', 'uni'],
    'XLM': ['stellar', 'xlm'],
    'ETC': ['ethereum classic', 'etc'],
    'ATOM': ['cosmos', 'atom'],
    'NEAR': ['near'],
    'FIL': ['filecoin', 'fil'],
    'HBAR': ['hedera', 'hbar'],
    'ICP': ['internet computer', 'icp'],
    'AAVE': ['aave'],
    'EGLD': ['elrond', 'egld'],
    'VET': ['vechain', 'vet'],
    'SAND': ['sandbox', 'sand'],
    'MANA': ['decentraland', 'mana'],
    'XTZ': ['tezos', 'xtz']
}

EMOJI_KEYWORDS: Dict[str, List[str]] = {
    "₿": ["bitcoin", "btc"],
    "⚙️": ["ethereum", "eth"],
    "📡": ["ton"],
    "✈️": ["telegram"],
    "🚨": ["scam", "hack", "urgent", "breaking", "فوری", "مهم"],
    "🐳": ["نهنگ"],
    "🟢": ["price rise", "price increase", "رشد قیمت", "افزایش قیمت", "صعود"],
    "🔴": ["price drop", "price decrease", "کاهش قیمت", "نزول", "افت"],
    "📰": ["study", "research", "analysis", "مقاله", "مطالعه", "تحلیل"],
    "🎮": ["playtoearn", "game", "p2e", "gaming"],
    "🎁": ["airdrop"],
    "📌": []
}

SOURCE_HASHTAGS: Dict[str, str] = {
    'u.today': '#UToday',
    'cointelegraph.com': '#Cointelegraph',
    'decrypt.co': '#Decrypt',
    'news.bitcoin.com': '#BitcoinNews',
    'telegram.org': '#Telegram',
    'playtoearn.net': '#PlayToEarn',
    'airdrops.io': '#Airdrops',
    'cryptopanic.com': '#CryptoPanic'
}

feed_urls = [
    'https://u.today/rss',
    'https://cointelegraph.com/rss',
    'https://decrypt.co/feed',
    'https://news.bitcoin.com/feed',
    'https://telegram.org/blog/rss',
    'https://playtoearn.net/feed/',
    'https://airdrops.io/feed/'
]

sent_links_file = 'sent_links.txt'

session = requests.Session()


def extract_main_image(url: str) -> Optional[str]:
    try:
        res = session.get(url, timeout=10)
        soup = BeautifulSoup(res.content, 'html.parser')
        image = soup.find('meta', property='og:image')
        if image and image.has_attr('content'):
            return image['content']
    except Exception as e:
        print(f"⚠️ خطا در استخراج تصویر اصلی از {url}: {e}")
    return None


def extract_currency_tags(text: str) -> str:
    tags: Set[str] = set()
    text_lower = text.lower()
    for symbol, keywords in CURRENCY_KEYWORDS.items():
        if any(keyword in text_lower for keyword in keywords):
            tags.add(f"#{symbol}")
    return ' '.join(sorted(tags))


def clean_domain(url: str) -> str:
    domain = re.sub(r'^https?://(www\.)?', '', url).split('/')[0]
    domain = re.sub(r'\.(com|org|net|co)$', '', domain)
    return domain


def translate_to_farsi(text: str) -> str:
    try:
        source_lang = detect(text)
    except:
        source_lang = 'en'

    translators = [
        ("MyMemory", "https://api.mymemory.translated.net/get",
         {'q': text, 'langpair': f'{source_lang}|fa'}),
        ("LibreTranslate", "https://libretranslate.de/translate",
         {'q': text, 'source': source_lang, 'target': 'fa', 'format': 'text'}),
        ("Translate.astian", "https://translate.astian.org/translate",
         {'q': text, 'source': source_lang, 'target': 'fa', 'format': 'text'}),
        ("OpensourceTranslation", "https://translate.argosopentech.com/translate",
         {'q': text, 'source': source_lang, 'target': 'fa', 'format': 'text'})
    ]

    for name, url, payload in translators:
        try:
            if "get" in url:
                res = session.get(url, params=payload, timeout=10)
            else:
                res = session.post(url, json=payload, timeout=10)
            if res.status_code == 200:
                data = res.json()
                translated = data.get('translatedText') or data.get('responseData', {}).get('translatedText')
                if translated and detect(translated) == 'fa':
                    return translated
        except Exception:
            continue

    return text


def get_news_emoji(title: str, summary: str) -> str:
    text = (title + ' ' + summary).lower()
    for emoji, keywords in EMOJI_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return emoji
    return "📌"


def load_sent_links() -> Set[str]:
    try:
        with open(sent_links_file, 'r') as f:
            return set(f.read().splitlines())
    except FileNotFoundError:
        return set()


def save_sent_links(links: Set[str]):
    with open(sent_links_file, 'w') as f:
        f.write('\n'.join(links))


def send_telegram_message(title: str, summary: str, link: str, image_url: Optional[str], site: str):
    tags = extract_currency_tags(title + ' ' + summary)
    domain = clean_domain(site)
    hashtag = SOURCE_HASHTAGS.get(domain, '')
    message_link = f'<a href="{link}">{domain}</a>'
    emoji = get_news_emoji(title, summary)

    message = (
        f"{emoji} <b>{title}</b>\n\n{summary}\n\n{tags} {hashtag}\n\n"
        f"{message_link}\n<blockquote>📱 {CHANNEL_HANDLE}</blockquote>"
    )

    payload = {
        'chat_id': CHANNEL_HANDLE,
        'text': message,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True
    }

    if image_url:
        payload_photo = {
            'chat_id': CHANNEL_HANDLE,
            'photo': image_url,
            'caption': message,
            'parse_mode': 'HTML'
        }
        try:
            r = session.post(f'https://api.telegram.org/bot{TOKEN}/sendPhoto', data=payload_photo, timeout=10)
            if r.status_code != 200:
                session.post(f'https://api.telegram.org/bot{TOKEN}/sendMessage', data=payload, timeout=10)
        except Exception as e:
            print(f"⚠️ خطا در ارسال عکس به تلگرام: {e}")
            session.post(f'https://api.telegram.org/bot{TOKEN}/sendMessage', data=payload, timeout=10)
    else:
        try:
            session.post(f'https://api.telegram.org/bot{TOKEN}/sendMessage', data=payload, timeout=10)
        except Exception as e:
            print(f"⚠️ خطا در ارسال پیام به تلگرام: {e}")


def fetch_cryptopanic_news(sent_links: Set[str]) -> List[Dict[str, str]]:
    url = (
        f"https://cryptopanic.com/api/v1/posts/?auth_token={CRYPTO_PANIC_TOKEN}"
        f"&public=true&region=international&kind=news&media=true"
    )
    news_items = []
    try:
        res = session.get(url, timeout=10)
        posts = res.json().get("results", [])
        for post in posts:
            link = post.get("url")
            if not link or link in sent_links:
                continue
            title = post.get("title", "")
            content = post.get("content") or post.get("body") or ""
            summary = re.sub('<[^<]+?>', '', content).strip()
            news_items.append({"title": title, "summary": summary, "link": link})
    except Exception as e:
        print(f"⚠️ خطا در دریافت اخبار CryptoPanic: {e}")
    return news_items


def fetch_and_send_all():
    print("🔍 بررسی همه منابع خبر...")
    sent_links = load_sent_links()
    new_news_found = False

    for url in feed_urls:
        feed = feedparser.parse(url)
        print(f"منبع: {url} - تعداد خبرها: {len(feed.entries)}")
        for entry in feed.entries[:3]:
            if entry.link in sent_links:
                continue

            title_en = entry.title
            summary_en = re.sub('<[^<]+?>', '', entry.summary or '').strip()

            title = translate_to_farsi(title_en)
            summary = translate_to_farsi(summary_en)
            image_url = extract_main_image(entry.link)

            send_telegram_message(title, summary, entry.link, image_url, url)
            sent_links.add(entry.link)
            new_news_found = True

            if len(sent_links) > 200:
                sent_links = set(list(sent_links)[-200:])

    crypto_news = fetch_cryptopanic_news(sent_links)
    for news in crypto_news:
        if news["link"] in sent_links:
            continue

        title = translate_to_farsi(news["title"])
        summary = translate_to_farsi(news["summary"])
        image_url = extract_main_image(news["link"])

        send_telegram_message(title, summary, news["link"], image_url, "cryptopanic.com")
        sent_links.add(news["link"])
        new_news_found = True

        if len(sent_links) > 200:
            sent_links = set(list(sent_links)[-200:])

    save_sent_links(sent_links)
    return new_news_found

# Felsefemiz Bot

Felsefe sözleri üreten, görsel oluşturan ve WordPress + sosyal medyaya otomatik yayınlayan bot.

## Kurulum

Railway'de şu environment variable'ları tanımlayın:

```
ANTHROPIC_API_KEY=
TELEGRAM_TOKEN=
TELEGRAM_CHAT_ID=
TWITTER_CONSUMER_KEY=
TWITTER_CONSUMER_SECRET=
TWITTER_ACCESS_TOKEN=
TWITTER_ACCESS_SECRET=
WP_URL=https://felsefemiz.net
WP_USER=serezart
WP_APP_PASS=
META_ACCESS_TOKEN=
INSTAGRAM_ACCOUNT_ID=
FACEBOOK_PAGE_ID=
IMGBB_API_KEY=
```

## Çalıştırma

```bash
pip install -r requirements.txt
python bot.py
```

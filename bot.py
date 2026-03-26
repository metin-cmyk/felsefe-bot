# -*- coding: utf-8 -*-
"""
Telegram Bot Ana Dosyası — Felsefemiz.net
/yeni komutuyla söz üretir, görsel oluşturur ve WordPress'e atar.
"""
import os, time, logging, threading
import telebot
import schedule

from quote_generator import generate_quote
from image_generator import create_post_image
from publishers import post_to_wordpress

# Log ayarları
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# Railway Environment Variables
TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if not TOKEN:
    log.error("TELEGRAM_TOKEN bulunamadı! Bot çalıştırılamıyor.")
    exit(1)

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Felsefemiz Bot aktif! 🏛️\nYeni söz üretmek ve siteye eklemek için /yeni komutunu kullanabilirsin.")

@bot.message_handler(commands=['yeni'])
def handle_yeni(message):
    # Eğer CHAT_ID tanımlıysa ve komut başka yerden gelirse reddet (Güvenlik)
    if CHAT_ID and str(message.chat.id) != str(CHAT_ID):
        bot.reply_to(message, "Yetkisiz kullanım.")
        return

    bot.reply_to(message, "⏳ Felsefi söz üretiliyor, görsel hazırlanıyor ve WordPress'e yükleniyor. Bu işlem 1-2 dakika sürebilir...")
    
    try:
        # 1. Sözü Üret
        quote_data = generate_quote()
        if not quote_data:
            bot.send_message(message.chat.id, "❌ Uygun bir söz üretilemedi. Logları kontrol et.")
            return

        # 2. Görseli Oluştur
        post_img, palette = create_post_image(quote_data)
        
        # 3. WordPress'e Yükle
        url, post_id, media_id = post_to_wordpress(quote_data, post_img)

        # 4. Sonucu Telegram'a Bildir
        if url:
            msg = f"✅ **Yeni Söz Başarıyla Yayınlandı!**\n\n"
            msg += f"👤 *Yazar:* {quote_data.get('author')}\n"
            msg += f"📜 *Söz:* {quote_data.get('quote')[:80]}...\n\n"
            msg += f"🔗 [Sitede Gör]({url})"
            
            # Görseli de Telegram'dan gönder
            with open(post_img, 'rb') as photo:
                bot.send_photo(message.chat.id, photo, caption=msg, parse_mode='Markdown')
        else:
            bot.send_message(message.chat.id, "⚠️ Söz üretildi ve görsel hazırlandı ancak WordPress'e yüklenirken bir sorun oluştu.")

    except Exception as e:
        log.error("Bot /yeni komutu hatası: %s" % e, exc_info=True)
        bot.send_message(message.chat.id, f"❌ Kritik bir hata oluştu:\n{str(e)}")

def run_scheduler():
    """Otomatik zamanlanmış görevleri çalıştıran döngü"""
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    log.info("Telegram Bot başlatılıyor...")
    
    # Eğer günde 1 kere otomatik paylaşım istersen aşağıdaki satırın başındaki '#' işaretini kaldırıp düzenleyebilirsin:
    # schedule.every().day.at("10:00").do(lambda: handle_yeni(type('obj', (object,), {'chat': type('obj', (object,), {'id': CHAT_ID})()})))
    
    # Zamanlayıcıyı ayrı bir thread'de (arka planda) başlat
    threading.Thread(target=run_scheduler, daemon=True).start()
    
    # Botu sürekli dinleme modunda tut
    bot.infinity_polling(timeout=10, long_polling_timeout=5)

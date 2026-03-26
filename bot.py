# -*- coding: utf-8 -*-
"""
Telegram Bot Ana Dosyası — Felsefemiz.net
/yeni komutuyla söz üretir, POST ve STORY görseli oluşturur, WordPress'e atar.
"""
import os, time, logging, threading
import telebot
import schedule

from quote_generator import generate_quote
# Hem post hem story fonksiyonunu import ediyoruz
from image_generator import create_post_image, create_story_image 
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

    bot.reply_to(message, "⏳ Felsefi söz üretiliyor, Post ve Story görselleri hazırlanıyor... Bu işlem 1-2 dakika sürebilir.")
    
    try:
        # 1. Sözü Üret
        quote_data = generate_quote()
        if not quote_data:
            bot.send_message(message.chat.id, "❌ Uygun bir söz üretilemedi. Logları kontrol et.")
            return

        # 2. Görselleri Oluştur (Aynı renk paletiyle hem post hem story)
        post_img, palette = create_post_image(quote_data)
        story_img = create_story_image(quote_data, palette)
        
        # 3. WordPress'e Yükle
        url, post_id, media_id = post_to_wordpress(quote_data, post_img)

        # 4. TELEGRAM BİLDİRİMLERİ
        
        # A) Görselleri Gönder
        with open(post_img, 'rb') as p_file:
            bot.send_photo(message.chat.id, p_file, caption="📸 *Post Formatı*", parse_mode='Markdown')
            
        with open(story_img, 'rb') as s_file:
            bot.send_photo(message.chat.id, s_file, caption="📱 *Story Formatı*", parse_mode='Markdown')

        # B) Sosyal Medya Paylaşım Metni (Tek tıkla kopyalamak için kod bloğu içinde)
        full_quote = quote_data.get('quote', '')
        author = quote_data.get('author', '')
        hashtags = quote_data.get('hashtags', '')
        
        social_text = f"\"{full_quote}\"\n\n— {author}\n\n{hashtags}"
        
        copy_msg = f"📝 *Sosyal Medyada Paylaşmak İçin*\n_(Kopyalamak için aşağıdaki metnin üzerine bir kere dokunun)_:\n\n```text\n{social_text}\n```"
        bot.send_message(message.chat.id, copy_msg, parse_mode='Markdown')

        # C) WordPress Yayın Bildirimi
        if url:
            wp_msg = f"✅ **Sitede Başarıyla Yayınlandı!**\n🔗 [Buradan Kontrol Et]({url})"
            bot.send_message(message.chat.id, wp_msg, parse_mode='Markdown', disable_web_page_preview=True)
        else:
            bot.send_message(message.chat.id, "⚠️ Söz ve görseller hazırlandı ancak WordPress'e yüklenirken bir sorun oluştu.")

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
    
    # Zamanlayıcıyı ayrı bir thread'de (arka planda) başlat
    threading.Thread(target=run_scheduler, daemon=True).start()
    
    # Botu sürekli dinleme modunda tut
    bot.infinity_polling(timeout=10, long_polling_timeout=5)

import os
import telebot
from publishers import send_to_wordpress, send_to_telegram

# Railway Variables kısmından TELEGRAM_TOKEN değerini alır
TOKEN = os.getenv('TELEGRAM_TOKEN')
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def welcome(message):
    bot.reply_to(message, "Felsefe Botu Aktif!\n\nKullanım: /paylas Başlık | İçerik")

@bot.message_handler(commands=['paylas'])
def handle_paylas(message):
    try:
        # Gelen mesajı ayır
        raw_text = message.text.replace('/paylas ', '')
        if "|" not in raw_text:
            bot.reply_to(message, "Lütfen 'Başlık | İçerik' formatını kullanın.")
            return

        baslik, icerik = raw_text.split('|', 1)
        baslik = baslik.strip()
        icerik = icerik.strip()

        bot.reply_to(message, "⏳ Siteye yükleniyor...")

        # 1. Siteye (WordPress) Yükle
        success, wp_msg = send_to_wordpress(baslik, icerik)

        if success:
            # 2. Siteye yüklendiyse Telegram'a onay mesajı at
            bot.send_message(message.chat.id, f"✅ *Sitede Yayınlandı!*\n\n*Başlık:* {baslik}", parse_mode="Markdown")
        else:
            bot.reply_to(message, f"❌ Site yükleme hatası: {wp_msg}")

    except Exception as e:
        bot.reply_to(message, f"Bir hata oluştu: {str(e)}")

if __name__ == "__main__":
    print("Bot başlatılıyor...")
    bot.infinity_polling()

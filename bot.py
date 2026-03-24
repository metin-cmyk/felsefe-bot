import os
import telebot
from publishers import send_to_wordpress, send_to_telegram

# Railway Variables kısmından tokenı alır
TOKEN = os.getenv('TELEGRAM_TOKEN')
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Felsefe Botu Hazır!\n\nKullanım:\n/paylas Başlık | İçerik")

@bot.message_handler(commands=['paylas'])
def handle_paylas(message):
    try:
        # Mesajı Başlık ve İçerik olarak ayır
        raw_text = message.text.replace('/paylas ', '')
        if "|" not in raw_text:
            bot.reply_to(message, "Lütfen şu formatta yazın: /paylas Başlık | İçerik")
            return

        baslik, icerik = raw_text.split('|', 1)
        baslik = baslik.strip()
        icerik = icerik.strip()

        bot.reply_to(message, "⏳ İşlem başlatıldı, siteye yükleniyor...")

        # 1. ADIM: Siteye (WordPress) Gönder
        basari, sonuc_mesaji = send_to_wordpress(baslik, icerik)

        if basari:
            # 2. ADIM: Başarılıysa Telegram'a da bilgi ver
            onay_metni = f"✅ *Sitede Yayınlandı!*\n\n*Başlık:* {baslik}\n*İçerik:* {icerik[:100]}..."
            bot.send_message(message.chat.id, onay_metni, parse_mode="Markdown")
        else:
            # Hata varsa detaylı bildir
            bot.send_message(message.chat.id, f"❌ Siteye yüklenemedi!\n{sonuc_mesaji}")

    except Exception as e:
        bot.reply_to(message, f"Sistemsel bir hata oluştu: {str(e)}")

if __name__ == "__main__":
    print("Bot aktif ve dinlemede...")
    bot.infinity_polling()

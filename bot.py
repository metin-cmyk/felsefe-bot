import os
import telebot
from quote_generator import generate_quote 
from image_generator import create_post_image  # Logdaki öneriye göre düzeltildi
from publishers import send_to_wordpress, send_to_telegram

TOKEN = os.getenv('TELEGRAM_TOKEN')
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def welcome(message):
    bot.reply_to(message, "Felsefe Botu Hazır!\n/yeni - İçerik üretir\n/paylas Başlık | İçerik - Siteye yükler")

@bot.message_handler(commands=['yeni'])
def yeni_icerik(message):
    bot.reply_to(message, "📜 İçerik üretiliyor...")
    try:
        quote = generate_quote()
        # Logdaki hatayı gidermek için fonksiyon ismini create_post_image yaptım
        image_path = create_post_image(quote) 
        
        with open(image_path, 'rb') as photo:
            bot.send_photo(message.chat.id, photo, caption=f"Günün Sözü:\n\n{quote}")
    except Exception as e:
        bot.reply_to(message, f"Üretim hatası: {e}")

@bot.message_handler(commands=['paylas'])
def handle_paylas(message):
    try:
        raw_text = message.text.replace('/paylas ', '')
        if "|" not in raw_text:
            bot.reply_to(message, "Format: /paylas Başlık | İçerik")
            return
        baslik, icerik = raw_text.split('|', 1)
        bot.reply_to(message, "⏳ Siteye yükleniyor...")
        success, msg = send_to_wordpress(baslik.strip(), icerik.strip())
        if success:
            bot.send_message(message.chat.id, f"✅ Sitede yayınlandı: {baslik.strip()}")
        else:
            bot.reply_to(message, f"❌ Hata: {msg}")
    except Exception as e:
        bot.reply_to(message, f"Hata: {e}")

if __name__ == "__main__":
    bot.infinity_polling()

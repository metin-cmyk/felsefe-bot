import os, json, logging, telebot
from pathlib import Path
from datetime import datetime

# Senin orijinal dosyaların
from quote_generator import generate_quote
from image_generator import create_post_image, create_story_image
from publishers import post_to_wordpress

TOKEN = os.getenv('TELEGRAM_TOKEN')
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def welcome(message):
    bot.reply_to(message, "Felsefemiz Bot Aktif!\n/yeni - Yeni içerik üretir\n/paylas Başlık | İçerik - Manuel yükler")

@bot.message_handler(commands=['yeni'])
def yeni_icerik(message):
    bot.reply_to(message, "📜 İçerik ve görseller üretiliyor...")
    try:
        quote_data = generate_quote()
        # DOĞRU KULLANIM: Senin fonksiyonun tuple döndürür (Yol, Palet)
        post_img, palette = create_post_image(quote_data) 
        story_img = create_story_image(quote_data, palette)
        
        # Telegram'a gönder
        with open(post_img, 'rb') as photo:
            bot.send_photo(message.chat.id, photo, caption=f"Söz: {quote_data['quote']}\n\nYazar: {quote_data['author']}")
            
        # WordPress'e yükle (Opsiyonel)
        wp_link = post_to_wordpress(quote_data, post_img)
        if wp_link:
            bot.send_message(message.chat.id, f"✅ Siteye de yüklendi: {wp_link}")
            
    except Exception as e:
        bot.reply_to(message, f"Üretim hatası: {str(e)}")

@bot.message_handler(commands=['paylas'])
def handle_paylas(message):
    try:
        raw_text = message.text.replace('/paylas ', '')
        if "|" not in raw_text:
            bot.reply_to(message, "Format: Başlık | İçerik")
            return
        b, i = raw_text.split('|', 1)
        # Manuel paylaşım için basit sözlük yapısı
        q_data = {"quote": i.strip(), "author": b.strip()}
        
        bot.reply_to(message, "⏳ Siteye gönderiliyor...")
        # Senin orijinal image_generator'ını kullanarak görsel üretip yüklüyoruz
        p_img, pal = create_post_image(q_data)
        link = post_to_wordpress(q_data, p_img)
        
        if link:
            bot.send_message(message.chat.id, f"✅ Yayınlandı: {link}")
        else:
            bot.reply_to(message, "❌ WordPress yükleme başarısız.")
    except Exception as e:
        bot.reply_to(message, f"Hata: {e}")

if __name__ == "__main__":
    bot.infinity_polling()

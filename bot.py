# -*- coding: utf-8 -*-
"""
Telegram Bot Ana Dosyası — Felsefemiz.net
/start ile buton menüsü açılır.
Yeni Üret, Toplu Üret ve yayınlanan postu Silme özellikleri eklendi.
"""
import os, time, logging, threading
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import schedule

from quote_generator import generate_quote
from image_generator import create_post_image, create_story_image 
from publishers import post_to_wordpress, delete_from_wordpress
import toplu_uret  # Toplu üretim scriptini dahil ediyoruz

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

def get_main_keyboard():
    """Telegram sohbetinin altına sabitlenen ana menü butonları"""
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_yeni = KeyboardButton("🚀 Yeni Üret")
    btn_toplu = KeyboardButton("📚 Toplu Üret")
    markup.add(btn_yeni, btn_toplu)
    return markup

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Felsefemiz Bot aktif! 🏛️\nAşağıdaki butonları kullanarak işlem yapabilirsin.", reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: message.text in ["🚀 Yeni Üret", "📚 Toplu Üret", "/yeni"])
def handle_menu_buttons(message):
    # Güvenlik Kontrolü
    if CHAT_ID and str(message.chat.id) != str(CHAT_ID):
        bot.reply_to(message, "Yetkisiz kullanım.")
        return

    if message.text in ["🚀 Yeni Üret", "/yeni"]:
        process_yeni_uret(message)
    
    elif message.text == "📚 Toplu Üret":
        msg = bot.reply_to(message, "Kaç adet söz çekip veritabanına (DB) kaydetmek istiyorsun? Sadece sayı yaz (Örn: 20)")
        bot.register_next_step_handler(msg, process_toplu_uret_step)

def process_toplu_uret_step(message):
    """Toplu Üret komutundan sonra girilen sayıyı işler"""
    try:
        hedef = int(message.text)
        if hedef <= 0 or hedef > 100:
            bot.reply_to(message, "Lütfen 1 ile 100 arasında geçerli bir sayı gir.", reply_markup=get_main_keyboard())
            return
            
        bot.reply_to(message, f"⏳ {hedef} adet söz için toplu üretim arka planda başlatıldı. Bittiğinde sana haber vereceğim...", reply_markup=get_main_keyboard())
        
        # Sistemi kitlememesi için toplu üretimi arka planda (Thread) çalıştırıyoruz
        def run_toplu():
            toplu_uret.uret(hedef)
            bot.send_message(message.chat.id, f"✅ **Toplu üretim tamamlandı!** Hedeflenen {hedef} işlem döngüsü bitti.", parse_mode='Markdown')
        
        threading.Thread(target=run_toplu, daemon=True).start()

    except ValueError:
        bot.reply_to(message, "Geçersiz giriş yaptın, işlem iptal edildi.", reply_markup=get_main_keyboard())

def process_yeni_uret(message):
    """Tekli söz üretme, görsel basma ve yayınlama süreci"""
    bot.reply_to(message, "⏳ Felsefi söz üretiliyor, Post ve Story görselleri hazırlanıyor... Bu işlem 1-2 dakika sürebilir.", reply_markup=get_main_keyboard())
    
    try:
        # 1. Sözü Üret
        quote_data = generate_quote()
        if not quote_data:
            bot.send_message(message.chat.id, "❌ Uygun bir söz üretilemedi. Logları kontrol et.")
            return

        # 2. Görselleri Oluştur
        post_img, palette = create_post_image(quote_data)
        story_img = create_story_image(quote_data, palette)
        
        # 3. WordPress'e Yükle
        url, post_id, media_id = post_to_wordpress(quote_data, post_img)

        # 4. TELEGRAM BİLDİRİMLERİ
        with open(post_img, 'rb') as p_file:
            bot.send_photo(message.chat.id, p_file, caption="📸 *Post Formatı*", parse_mode='Markdown')
            
        with open(story_img, 'rb') as s_file:
            bot.send_photo(message.chat.id, s_file, caption="📱 *Story Formatı*", parse_mode='Markdown')

        # Kopya Metni
        social_text = f"\"{quote_data.get('quote', '')}\"\n\n— {quote_data.get('author', '')}\n\n{quote_data.get('hashtags', '')}"
        copy_msg = f"📝 *Sosyal Medyada Paylaşmak İçin*\n_(Kopyalamak için aşağıdaki metnin üzerine dokunun)_:\n\n```text\n{social_text}\n```"
        bot.send_message(message.chat.id, copy_msg, parse_mode='Markdown')

        # WP Yayın Bildirimi ve "Sil" Butonu
        if url and post_id:
            wp_msg = f"✅ **Sitede Başarıyla Yayınlandı!**\n🔗 [Buradan Kontrol Et]({url})"
            
            # Silme butonu için Inline (Mesaj altı) klavye oluşturuyoruz
            markup = InlineKeyboardMarkup()
            cb_data = f"del_{post_id}_{media_id}"
            markup.add(InlineKeyboardButton("🗑️ Siteden Sil", callback_data=cb_data))
            
            bot.send_message(message.chat.id, wp_msg, parse_mode='Markdown', disable_web_page_preview=True, reply_markup=markup)
        else:
            bot.send_message(message.chat.id, "⚠️ Söz ve görseller hazırlandı ancak WordPress'e yüklenirken bir sorun oluştu.")

    except Exception as e:
        log.error("Bot yeni üret hatası: %s" % e, exc_info=True)
        bot.send_message(message.chat.id, f"❌ Kritik bir hata oluştu:\n{str(e)}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('del_'))
def handle_delete_callback(call):
    """Siteden Sil butonuna tıklandığında çalışacak fonksiyon"""
    parts = call.data.split('_')
    if len(parts) >= 3:
        post_id = parts[1]
        media_id = parts[2] if parts[2] != 'None' else None
        
        bot.answer_callback_query(call.id, "🗑️ Silme işlemi başlatıldı, bekle...")
        
        deleted = delete_from_wordpress(post_id, media_id)
        
        if deleted:
            # Mesajı güncelleyip butonu kaldırıyoruz ki tekrar tıklanmasın
            bot.edit_message_text(f"✅ Yazı (ID: {post_id}) ve görsel WordPress'ten başarıyla silindi.", call.message.chat.id, call.message.message_id)
        else:
            bot.send_message(call.message.chat.id, "⚠️ Silme işlemi sırasında bir hata oluştu veya zaten silinmiş.")

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    log.info("Telegram Bot başlatılıyor...")
    threading.Thread(target=run_scheduler, daemon=True).start()
    bot.infinity_polling(timeout=10, long_polling_timeout=5)

# -*- coding: utf-8 -*-
"""
Telegram Bot Ana Dosyası
/start ile buton menüsü açılır.
Yeni Üret, Toplu Üret, Siteden Sil ve Sistem Durumu özellikleri eklendi.
"""
import os, time, logging, threading
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import schedule

from quote_generator import generate_quote
from image_generator import create_post_image, create_story_image 
from publishers import post_to_wordpress, delete_from_wordpress
import toplu_uret 
import db # Durum raporu için DB bağlantısı eklendi

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
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_yeni = KeyboardButton("🚀 Yeni Üret")
    btn_toplu = KeyboardButton("📚 Toplu Üret")
    btn_durum = KeyboardButton("📊 Sistem Durumu")
    markup.add(btn_yeni, btn_toplu, btn_durum)
    return markup

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Felsefemiz Bot aktif! 🏛️\nAşağıdaki butonları kullanarak işlem yapabilirsin.", reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: message.text in ["🚀 Yeni Üret", "📚 Toplu Üret", "📊 Sistem Durumu", "/yeni", "/durum"])
def handle_menu_buttons(message):
    # Güvenlik: Sadece senin Chat ID'n ile çalışır
    if CHAT_ID and str(message.chat.id) != str(CHAT_ID):
        bot.reply_to(message, "Yetkisiz kullanım.")
        return

    if message.text in ["🚀 Yeni Üret", "/yeni"]:
        process_yeni_uret(message)
    
    elif message.text == "📚 Toplu Üret":
        msg = bot.reply_to(message, "Kaç adet söz çekip veritabanına kaydetmek istiyorsun? (Örn: 20)")
        bot.register_next_step_handler(msg, process_toplu_uret_step)
        
    elif message.text in ["📊 Sistem Durumu", "/durum"]:
        process_durum(message)

def process_durum(message):
    """API ve Veritabanı durumunu test edip raporlar"""
    bot.reply_to(message, "🔍 Sistem, API kotaları ve veritabanı kontrol ediliyor. Lütfen bekle...", reply_markup=get_main_keyboard())
    threading.Thread(target=check_and_send_status, args=(message.chat.id,), daemon=True).start()

def check_and_send_status(chat_id):
    report = "📊 **Sistem ve API Raporu**\n\n"

    # 1. DB Durumu
    if db.test_connection():
        report += "🟢 **Veritabanı:** Bağlantı Aktif\n"
        soz_count = db.query("SELECT COUNT(*) as c FROM sozler", fetchone=True)
        try:
            yayin_count = db.query("SELECT COUNT(*) as c FROM yayinlar WHERE DATE(yayinlandi_at) = CURDATE()", fetchone=True)
            y_count = yayin_count['c'] if yayin_count else 0
        except:
            y_count = "Bilinmiyor"
            
        report += f"   └ Toplam Kayıtlı Söz: {soz_count['c'] if soz_count else 0}\n"
        report += f"   └ Bugün Yayınlanan: {y_count}\n\n"
    else:
        report += "🔴 **Veritabanı:** Bağlantı Kurulamadı!\n\n"

    # 2. Claude API Testi
    report += "🤖 **Yapay Zeka API Durumları:**\n"
    import anthropic
    c_key = os.environ.get("ANTHROPIC_API_KEY")
    if c_key:
        try:
            c_client = anthropic.Anthropic(api_key=c_key)
            # API'yi yormamak için sadece 1 kelimelik ping atılır
            c_client.messages.create(model="claude-sonnet-4-20250514", max_tokens=1, messages=[{"role": "user", "content": "ping"}])
            report += "🟢 **Claude API:** Aktif (Kredi Yeterli)\n"
        except Exception as e:
            if "credit balance is too low" in str(e).lower():
                report += "🔴 **Claude API:** Kredi Bitti!\n"
            else:
                report += f"🟡 **Claude API:** Hata ({str(e)[:30]})\n"
    else:
        report += "⚪ **Claude API:** Şifre (Key) Bulunamadı\n"

    # 3. Gemini API Testi
    from google import genai
    g_key = os.environ.get("GEMINI_API_KEY")
    if g_key:
        try:
            g_client = genai.Client(api_key=g_key)
            g_client.models.generate_content(model='gemini-2.0-flash', contents='ping')
            report += "🟢 **Gemini API:** Aktif (Kota Uygun)\n"
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                report += "🔴 **Gemini API:** Kota Dolu (Sınır Aşıldı)\n"
            else:
                report += f"🟡 **Gemini API:** Hata ({str(e)[:30]})\n"
    else:
        report += "⚪ **Gemini API:** Şifre (Key) Bulunamadı\n"

    report += "\n📝 *Not:* Sistem her zaman ilk olarak Claude'u dener. Claude'da kredi yoksa Gemini'ye geçer."
    
    bot.send_message(chat_id, report, parse_mode='Markdown')

def process_toplu_uret_step(message):
    try:
        hedef = int(message.text)
        if hedef <= 0 or hedef > 100:
            bot.reply_to(message, "Lütfen 1 ile 100 arasında geçerli bir sayı gir.", reply_markup=get_main_keyboard())
            return
            
        bot.reply_to(message, f"⏳ {hedef} adet söz için toplu üretim başlatıldı. Bittiğinde haber vereceğim...", reply_markup=get_main_keyboard())
        
        def run_toplu():
            toplu_uret.uret(hedef)
            bot.send_message(message.chat.id, f"✅ **Toplu üretim tamamlandı!** {hedef} işlem döngüsü bitti.", parse_mode='Markdown')
        
        threading.Thread(target=run_toplu, daemon=True).start()

    except ValueError:
        bot.reply_to(message, "Geçersiz giriş yaptın, işlem iptal edildi.", reply_markup=get_main_keyboard())

def process_yeni_uret(message):
    bot.reply_to(message, "⏳ Felsefi söz aranıyor, SEO makalesi yazılıyor ve görseller hazırlanıyor...", reply_markup=get_main_keyboard())
    
    try:
        quote_data = generate_quote()
        if not quote_data:
            bot.send_message(message.chat.id, "❌ Uygun bir söz üretilemedi veya API kotaları tamamen doldu. Lütfen /durum komutu ile kotaları kontrol et.")
            return

        post_img, palette = create_post_image(quote_data)
        story_img = create_story_image(quote_data, palette)
        
        url, post_id, media_id = post_to_wordpress(quote_data, post_img)

        with open(post_img, 'rb') as p_file:
            bot.send_photo(message.chat.id, p_file, caption="📸 *Post Formatı*", parse_mode='Markdown')
            
        with open(story_img, 'rb') as s_file:
            bot.send_photo(message.chat.id, s_file, caption="📱 *Story Formatı*", parse_mode='Markdown')

        social_text = f"\"{quote_data.get('quote', '')}\"\n\n— {quote_data.get('author', '')}\n\n{quote_data.get('hashtags', '')}"
        copy_msg = f"📝 *Sosyal Medyada Paylaşmak İçin*\n_(Kopyalamak için aşağıdaki metnin üzerine dokunun)_:\n\n```text\n{social_text}\n```"
        bot.send_message(message.chat.id, copy_msg, parse_mode='Markdown')

        if url and post_id:
            wp_msg = f"✅ **Sitede Başarıyla Yayınlandı!**\n🔗 [Buradan Kontrol Et]({url})"
            markup = InlineKeyboardMarkup()
            cb_data = f"del_{post_id}_{media_id}"
            markup.add(InlineKeyboardButton("🗑️ Siteden Sil", callback_data=cb_data))
            bot.send_message(message.chat.id, wp_msg, parse_mode='Markdown', disable_web_page_preview=True, reply_markup=markup)
        else:
            bot.send_message(message.chat.id, "⚠️ Söz ve görseller hazırlandı ancak WordPress'e yüklenirken sorun oluştu.")

    except Exception as e:
        log.error("Bot yeni üret hatası: %s" % e, exc_info=True)
        bot.send_message(message.chat.id, f"❌ Kritik bir hata oluştu:\n{str(e)}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('del_'))
def handle_delete_callback(call):
    parts = call.data.split('_')
    if len(parts) >= 3:
        post_id = parts[1]
        media_id = parts[2] if parts[2] != 'None' else None
        
        bot.answer_callback_query(call.id, "🗑️ Silme işlemi başlatıldı...")
        deleted = delete_from_wordpress(post_id, media_id)
        
        if deleted:
            bot.edit_message_text(f"✅ Yazı (ID: {post_id}) WordPress'ten başarıyla silindi.", call.message.chat.id, call.message.message_id)
        else:
            bot.send_message(call.message.chat.id, "⚠️ Silme işlemi sırasında bir hata oluştu.")

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    log.info("Telegram Bot başlatılıyor...")
    threading.Thread(target=run_scheduler, daemon=True).start()
    bot.infinity_polling(timeout=10, long_polling_timeout=5)

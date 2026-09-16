import streamlit as st
from datetime import datetime
from supabase import create_client, Client

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(
    page_config="Şube & Teknik Servis Takip",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- SUPABASE BAĞLANTISI ---
SUPABASE_URL = "https://suajufwixsofxgaknmjw.supabase.co"
SUPABASE_KEY = "sb_publishable_bj8_TtKr1o98hOu5GME-gw_6fduZTeu"

@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

# --- YARDIMCI FONKSİYONLAR ---
def tarih_formatla(iso_str):
    if not iso_str:
        return "-"
    try:
        dt = datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
        return dt.strftime("%d.%m.%Y %H:%M")
    except Exception:
        return str(iso_str)[:16]

def subeleri_getir():
    try:
        res = supabase.table("subeler").select("sube_adi").order("id", desc=False).execute()
        if res.data:
            return [s["sube_adi"] for s in res.data]
    except Exception:
        pass
    return ["Ana Servis", "Şube 1", "Şube 2"]

# --- OTURUM YÖNETİMİ (LOGIN) ---
if "aktif_personel" not in st.session_state:
    st.session_state.aktif_personel = None

if st.session_state.aktif_personel is None:
    st.title("🔐 Personel Girişi")
    st.markdown("Lütfen şube ve personel bilgilerinizle giriş yapın.")
    
    with st.form("login_form"):
        k_adi = st.text_input("Kullanıcı Adı")
        sifre = st.text_input("Şifre", type="password")
        submit = st.form_submit_button("Giriş Yap")
        
        if submit:
            if not k_adi or not sifre:
                st.warning("Lütfen kullanıcı adı ve şifrenizi girin.")
            else:
                try:
                    res = supabase.table("personeller").select("*").eq("kullanici_adi", k_adi).eq("sifre", sifre).execute()
                    if res.data and len(res.data) > 0:
                        st.session_state.aktif_personel = res.data[0]
                        st.rerun()
                    else:
                        st.error("Kullanıcı adı veya şifre hatalı!")
                except Exception as e:
                    st.error(f"Bağlantı hatası: {e}")
    st.stop()

# --- ANA UYGULAMA (GİRİŞ YAPILDIKTAN SONRA) ---
personel = st.session_state.aktif_personel
kullanici_etiketi = f"{personel['ad_soyad']} ({personel['sube']})"

# Üst Bilgi ve Çıkış Butonu
col_head1, col_head2 = st.columns([4, 1])
with col_head1:
    st.title("📱 Şube & Teknik Servis Takip Sistemi")
    st.caption(f"👤 Aktif Personel: **{kullanici_etiketi}**")
with col_head2:
    if st.button("🚪 Çıkış Yap", use_container_width=True):
        st.session_state.aktif_personel = None
        st.rerun()

st.divider()

# --- SOL / ÜST KISIM: YENİ CİHAZ EKLEME & FİLTRELER ---
with st.expander("➕ Yeni Cihaz Kaydı Oluştur", expanded=False):
    sube_listesi = subeleri_getir()
    with st.form("yeni_cihaz_form"):
        f_col1, f_col2, f_col3 = st.columns(3)
        with f_col1:
            secilen_sube = st.selectbox("Şube", sube_listesi, index=sube_listesi.index(personel["sube"]) if personel["sube"] in sube_listesi else 0)
            marka = st.text_input("Marka (Apple, Samsung vb.)")
        with f_col2:
            musteri = st.text_input("Müşteri Adı Soyadı")
            model = st.text_input("Cihaz Model (iPhone 11 vb.)")
        with f_col3:
            telefon = st.text_input("Müşteri Telefonu")
            sifre = st.text_input("Ekran Şifresi / Desen")
            
        ariza = st.text_area("Arıza / Şikayet Detayı")
        kaydet_btn = st.form_submit_button("Cihazı Kaydet", use_container_width=True)
        
        if kaydet_btn:
            if not musteri or not model:
                st.warning("Lütfen müşteri adı ve cihaz modelini girin.")
            else:
                now_iso = datetime.now().isoformat()
                try:
                    supabase.table("cihazlar").insert({
                        "sube": secilen_sube,
                        "musteri_adi": musteri,
                        "telefon": telefon if telefon else "Belirtilmedi",
                        "ekran_sifresi": sifre if sifre else "Yok",
                        "marka": marka,
                        "cihaz_model": model,
                        "ariza": ariza,
                        "durum": "İşlemde",
                        "ekleyen_personel_id": int(personel["id"]),
                        "kayit_tarihi": now_iso,
                        "son_etkilesim": now_iso
                    }).execute()
                    st.success("Cihaz başarıyla kaydedildi!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Kayıt eklenirken hata oluştu: {e}")

st.subheader("📋 Servisteki Cihazlar Listesi")

# Filtreleme Alanı
flt_col1, flt_col2 = st.columns([2, 3])
with flt_col1:
    durum_filtre = st.selectbox("Duruma Göre Filtrele", ["Tümü", "İşlemde", "Hazır", "Teslim Edildi", "İade Edildi"])
with flt_col2:
    arama_sorgusu = st.text_input("🔍 Hızlı Arama (Müşteri, Telefon, Model)", "")

# Cihazları Çek
try:
    query = supabase.table("cihazlar").select("*")
    if durum_filtre != "Tümü":
        query = query.eq("durum", durum_filtre)
    res = query.order("id", desc=True).execute()
    cihazlar = res.data if res.data else []
except Exception as e:
    st.error(f"Cihazlar listelenemedi: {e}")
    cihazlar = []

# Arama Filtrelemesi
if arama_sorgusu:
    q_lower = arama_sorgusu.lower()
    cihazlar = [
        c for c in cihazlar if 
        q_lower in str(c.get("musteri_adi", "")).lower() or 
        q_lower in str(c.get("telefon", "")).lower() or 
        q_lower in str(c.get("cihaz_model", "")).lower()
    ]

if not cihazlar:
    st.info("Listelenecek kayıt bulunamadı.")
else:
    # 1. TÜM KAYITLARI TABLO OLARAK GÖSTER
    st.dataframe(
        cihazlar,
        column_config={
            "id": "ID",
            "sube": "Şube",
            "musteri_adi": "Müşteri",
            "telefon": "Telefon",
            "marka": "Marka",
            "cihaz_model": "Model",
            "durum": "Durum",
            "kayit_tarihi": "Kayıt Tarihi"
        },
        use_container_width=True,
        hide_index=True
    )
    
    st.markdown("---")
    st.markdown("### ⚙️ Cihaz Detayı ve İşlemler")
    
    # İşlem yapılacak cihazı ID'ye göre seçme
    secilen_id = st.selectbox(
        "İşlem Yapılacak Cihazı Seçin (ID - Müşteri - Model)", 
        [c['id'] for c in cihazlar],
        format_func=lambda x: f"ID: #{x} | " + " - ".join([str(c['musteri_adi']), str(c['cihaz_model']), str(c['durum'])]) for c in cihazlar if c['id'] == x
    )
    
    secili_c = next(c for c in cihazlar if c['id'] == secilen_id)

    col_detay1, col_detay2 = st.columns(2)
    
    with col_detay1:
        st.markdown("### 📌 Cihaz Bilgileri")
        st.write(f"**Şube:** {secili_c.get('sube')}")
        st.write(f"**Müşteri:** {secili_c.get('musteri_adi')} ({secili_c.get('telefon')})")
        st.write(f"**Cihaz:** {secili_c.get('marka')} {secili_c.get('cihaz_model')}")
        st.write(f"**Ekran Şifresi:** {secili_c.get('ekran_sifresi')}")
        st.write(f"**Arıza:** {secili_c.get('ariza')}")
        st.write(f"**Kayıt Tarihi:** {tarih_formatla(secili_c.get('kayit_tarihi'))}")
        
        # Durum Güncelleme
        yeni_durum = st.selectbox("Durum Güncelle", ["İşlemde", "Hazır", "Teslim Edildi", "İade Edildi"], index=["İşlemde", "Hazır", "Teslim Edildi", "İade Edildi"].index(secili_c.get('durum', 'İşlemde')))
        if st.button("Durumu Kaydet"):
            try:
                now_iso = datetime.now().isoformat()
                supabase.table("cihazlar").update({"durum": yeni_durum, "son_etkilesim": now_iso}).eq("id", secili_c['id']).execute()
                
                # Not ekle
                supabase.table("mesajlar").insert({
                    "cihaz_id": secili_c['id'],
                    "gonderen": kullanici_etiketi,
                    "mesaj": f"🔄 DURUM GÜNCELLENDİ: {yeni_durum}"
                }).execute()
                
                st.success("Durum güncellendi!")
                st.rerun()
            except Exception as e:
                st.error(f"Hata: {e}")

        # Silme Yetkisi Kontrolü
        is_ana_servis = personel.get("sube") == "Ana Servis"
        is_ekleyen = str(secili_c.get("ekleyen_personel_id")) == str(personel["id"])
        
        if is_ana_servis or is_ekleyen:
            if st.button("🗑️ Bu Cihazı Sil", type="primary"):
                try:
                    supabase.table("cihazlar").delete().eq("id", secili_c['id']).execute()
                    st.success("Cihaz silindi!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Silinemedi: {e}")

    with col_detay2:
        st.markdown("### 💬 Notlar ve İletişim Geçmişi")
        
        # Mesajları Çek
        try:
            m_res = supabase.table("mesajlar").select("*").eq("cihaz_id", secili_c['id']).order("id", desc=False).execute()
            mesajlar = m_res.data if m_res.data else []
        except Exception:
            mesajlar = []
            
        # Mesaj Kutusu Görünümü
        chat_container = st.container(height=250)
        with chat_container:
            if not mesajlar:
                st.caption("Henüz not eklenmemiş.")
            else:
                for m in mesajlar:
                    st.markdown(f"**{m.get('gonderen')}**: {m.get('mesaj')}")
                    st.markdown("---")
                    
        # Yeni Not Gönderme
        yeni_not = st.text_input("Cihaz için bir not yazın...", key="input_not")
        if st.button("Not Gönder"):
            if yeni_not.strip():
                try:
                    now_iso = datetime.now().isoformat()
                    supabase.table("mesajlar").insert({
                        "cihaz_id": secili_c['id'],
                        "gonderen": kullanici_etiketi,
                        "mesaj": yeni_not.strip()
                    }).execute()
                    supabase.table("cihazlar").update({"son_etkilesim": now_iso}).eq("id", secili_c['id']).execute()
                    st.rerun()
                except Exception as e:
                    st.error(f"Not gönderilemedi: {e}")

"""
BIST ESv1 Strateji Tarama — Günlük Periyot
────────────────────────────────────────────
Mantık: Akşam seans kapandıktan sonra çalıştır.
        AL sinyali veren hisseler ertesi gün için listelenir.
        Mum kapanışı beklenir (barstate.isconfirmed mantığı).

Kurulum:
  pip install yfinance pandas numpy openpyxl
Çalıştırma:
  python bist_tarama.py
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
import logging
warnings.filterwarnings("ignore")
logging.getLogger("yfinance").setLevel(logging.CRITICAL)

# ─────────────────────────────────────────────
# PARAMETRELER
# ─────────────────────────────────────────────
INTERVAL    = "1d"     # Günlük periyot
PERIOD_1D   = "120d"   # Son 120 gün (hesaplama için yeterli)
PERIOD_HTF  = "300d"
MED_LEN     = 3
RSI_LEN     = 14
STOCH_LEN   = 14
SMOOTH_K    = 3
SMOOTH_D    = 3
EMA_LEN     = 14
LOOKBACK    = 4
VOL_LEN     = 20
HTF_MA_LEN  = 200

USE_HTF     = False    # Varsayılan OFF
USE_VOLUME  = False    # Varsayılan OFF

# ─────────────────────────────────────────────
# BIST HİSSE LİSTESİ
# ─────────────────────────────────────────────
BIST_HISSELER = sorted(list(set([
    "ACSEL","ADEL","AEFES","AFYON","AGESA","AGHOL","AKBNK","AKCNS","AKFYE",
    "AKGRT","AKMGY","AKSA","AKSEN","AKSGY","ALARK","ALBRK","ALFAS","ALKIM",
    "ALMAD","ALVARK","ANELE","ARCLK","ARDYZ","ARENA","ARSAN","ASELS","ASTOR",
    "ATEKS","AYGAZ","BAGFS","BAKAB","BANVT","BERA","BFREN","BIMAS","BJKAS",
    "BOSSA","BRISA","BRMEN","BRSAN","BTCIM","BUCIM","BURCE","BURVA","CCOLA",
    "CELHA","CEMAS","CEMTS","CIMSA","CLEBI","CONAS","CWENE","DEVA","DITAS",
    "DMSAS","DOAS","DOBUR","DOHOL","DOKTA","DYOBY","ECILC","ECZYT","EGEEN",
    "EGEPO","EGGUB","EGPRO","EKGYO","EREGL","FROTO","GARAN","GENIL","GENTS",
    "GEREL","GESAN","GOLTS","GOODY","GOZDE","GUBRF","HALKB","HATEK","HEKTS",
    "HUBVC","HURGZ","ICBCT","INDES","INFO","INVEO","ISDMR","ISFIN","ISGYO",
    "ISKUR","JANTS","KAREL","KARSN","KARTN","KCHOL","KLKIM","KLMSN","KLSYN",
    "KONYA","KORDS","KOZAA","KOZAL","KRDMA","KRDMB","KRDMD","LOGO","MAALT",
    "MAGEN","MAKIM","MARKA","MAVKG","MEDTR","MEPET","MERCN","MERIT","MERKO",
    "METRO","MIGROS","MNDRS","MOBTL","MPARK","MRSHL","NATEN","NETAS","NTGAZ",
    "NTHOL","NTTUR","NUHCM","ODAS","ORGE","ORMA","OTKAR","OYAKC","PETKM",
    "PETUN","PGSUS","PKART","POLHO","PRKAB","PRKME","QNBFB","RYSAS","SAHOL",
    "SANEL","SANKO","SARKY","SASA","SISE","SKBNK","SKTAS","SOKM","TCELL",
    "THYAO","TKFEN","TOASO","TTKOM","TTRAK","TUPRS","TURGG","VAKBN","VAKKO",
    "VESBE","VESTL","YKBNK","YONGA","ZOREN","AKENR","AKFGY","ANHYT","ARAT",
    "ATATP","AVGYO","AYCES","AYEN","BASGZ","BAYRK","BIENY","BINBN","BIOEN",
    "BIZIM","BLCYT","BNTAS","BRYAT","BVSAN","CANTE","CEOEM","CLKHO","CRFSA",
    "CUSAN","CVKMD","DAGHL","DAGI","DAPGM","DARDL","DENGE","DERHL","DESA",
    "DESPC","DGATE","DGGYO","DGNMO","DNISI","DURDO","DZGYO","EDATA","EDIP",
    "EMKEL","EMNIS","ENPRO","ENRUY","ERSU","ESCAR","ESCOM","ESEN","ETILR",
    "EUREN","EUYO","EVCIL","FADE","FENER","FLAP","FONET","FORMT","FORTE",
    "FZLGY","GARFA","GEDIK","GEDZA","GLBMD","GLCVY","GLYHO","GMTAS","GOKNR",
    "GRNYO","GRSEL","GRTRK","GSDDE","GSDHO","GSRAY","GWIND","GZNMI","HDFGS",
    "HEDEF","HKTM","HLGYO","HPGYO","HRKET","HTTBT","HUNER","IDGYO","IEYHO",
    "IHLGM","IHEVA","IHGZT","IHLAS","IMASM","INTEM","IPEKE","ISGSY","ISKPL",
    "ISMO","ISYAT","ITTFH","IZFAS","IZINV","IZMDC","KAPLM","KATMR","KAYSE",
    "KBORU","KCAER","KENT","KERVN","KERVT","KFEIN","KGYO","KIMMR","KLGYO",
    "KLNMA","KLRHO","KLSER","KMPUR","KNFRT","KOCMT","KOPOL","KRONT","KRPLS",
    "KRSTL","KRTEK","KRVGD","KTLEV","KTSKR","KUTPO","KUVVA","KUYAS","LIDER",
    "LIDFA","LILAK","LKMNH","LMKDC","LRSHO","LUKSK","MACKO","MANAS","MARTI",
    "MEGAP","METUR","MIATK","MMCAS","MNDTR","MOGAN","MRGYO","MSGYO","MTRKS",
    "MZHLD","NIBAS","NUGYO","OBAMS","OBASE","ODINE","OFKGT","ONCSM","ORCAY",
    "OSMEN","OSTIM","OYAYO","OYLUM","OZGYO","OZKGY","OZRDN","OZSUB","PAGYO",
    "PAMEL","PAPIL","PARSN","PASEU","PCILT","PEGYO","PEKMT","PENGD","PENTA",
    "PINSU","PKENT","PLTUR","PNLSN","POLTK","PRDGS","PRZMA","PSDTC","PSGYO",
    "QNBFL","RALYH","RAYSG","RHEAG","RNPOL","RODRG","ROYAL","RTALB","RUBNS",
    "SAYAS","SDTTR","SEGYO","SEKFK","SEKUR","SELEC","SELGD","SELVA","SEYKM",
    "SILVR","SMART","SMRTG","SNGYO","SNICA","SNKRN","SONME","SRVGY","SUMAS",
    "SUNTK","SUWEN","TABGD","TARKM","TATEN","TATGD","TAVHL","TBORG","TDGYO",
    "TEKTU","TERA","TETMT","TGSAS","TKNSA","TLMAN","TMSN","TNZTP","TRCAS",
    "TRGYO","TRILC","TSGYO","TSPOR","TUCLK","TUKAS","ULUUN","ULUSE","UMPAS",
    "UNLU","USAK","VAKFN","VANGD","VBTYZ","VERUS","VKFYO","VKGYO","VKING",
    "YATAS","YAYLA","YBTAS","YEOTK","YGGYO","YKSLN","YOYGD","YPKYO","YUNSA",
    "ZEDUR","ZRGYO"
])))

# ─────────────────────────────────────────────
# FONKSİYONLAR
# ─────────────────────────────────────────────
def percentile_nearest_rank(series, length, pct):
    result = series.copy() * np.nan
    arr    = series.values
    for i in range(length - 1, len(arr)):
        w = arr[i - length + 1:i + 1]
        w = w[~np.isnan(w)]
        if len(w) == 0:
            continue
        idx = int(np.ceil(pct / 100.0 * len(w))) - 1
        result.iloc[i] = np.sort(w)[max(0, min(idx, len(w)-1))]
    return result

def ema(series, length):
    return series.ewm(span=length, adjust=False).mean()

def sma(series, length):
    return series.rolling(window=length).mean()

def rsi_calc(close, length):
    delta    = close.diff()
    gain     = delta.clip(lower=0)
    loss     = (-delta).clip(lower=0)
    avg_gain = gain.ewm(com=length-1, adjust=False).mean()
    avg_loss = loss.ewm(com=length-1, adjust=False).mean()
    rs       = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def stoch_rsi(close, rsi_len, stoch_len, smooth_k, smooth_d):
    rsi_val   = rsi_calc(close, rsi_len)
    rsi_min   = rsi_val.rolling(stoch_len).min()
    rsi_max   = rsi_val.rolling(stoch_len).max()
    stoch_raw = (rsi_val - rsi_min) / (rsi_max - rsi_min + 1e-10) * 100
    K         = sma(stoch_raw, smooth_k)
    D         = sma(K, smooth_d)
    return K, D

def crossover_win(a, b, n):
    cross = (a > b) & (a.shift(1) <= b.shift(1))
    return cross.rolling(n).max().astype(bool)

def veri_cek(ticker, period, interval):
    df = yf.download(ticker, period=period, interval=interval,
                     progress=False, auto_adjust=True)
    if df is None or len(df) == 0:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

def htf_ok(ticker):
    try:
        df = veri_cek(ticker, PERIOD_HTF, "1d")
        if df is None or len(df) < HTF_MA_LEN + 5:
            return True
        close = df["Close"]
        ma    = sma(close, HTF_MA_LEN)
        return bool(float(close.iloc[-1]) > float(ma.iloc[-1]))
    except:
        return True

def sinyal_hesapla(df):
    high  = df["High"]
    low   = df["Low"]
    close = df["Close"]
    vol   = df["Volume"]
    hl2   = (high + low) / 2

    median     = percentile_nearest_rank(hl2, MED_LEN, 50)
    median_ema = ema(median, MED_LEN)

    K, D  = stoch_rsi(close, RSI_LEN, STOCH_LEN, SMOOTH_K, SMOOTH_D)
    ema_k = ema(K, EMA_LEN)

    c1 = crossover_win(median, median_ema, LOOKBACK)
    c2 = crossover_win(K, D, LOOKBACK)
    c3 = crossover_win(K, ema_k, LOOKBACK)

    vol_ok    = (vol > sma(vol, VOL_LEN)) if USE_VOLUME else pd.Series(True, index=close.index)
    long_raw  = c1 & c2 & c3 & vol_ok
    sat_raw   = (K < ema_k) & (K.shift(1) >= ema_k.shift(1))

    # Pozisyon acikken tekrar AL uretmemek icin gunluk AL/SAT akisini takip et.
    al_sinyal  = pd.Series(False, index=close.index)
    sat_sinyal = pd.Series(False, index=close.index)
    pozisyon_acik = False

    for i in range(len(close)):
        if not pozisyon_acik and bool(long_raw.iloc[i]):
            al_sinyal.iloc[i] = True
            pozisyon_acik = True
        elif pozisyon_acik and bool(sat_raw.iloc[i]):
            sat_sinyal.iloc[i] = True
            pozisyon_acik = False

    return al_sinyal, sat_sinyal, close

# ─────────────────────────────────────────────
# ANA TARAMA
# ─────────────────────────────────────────────
def tara():
    print("\n" + "="*60)
    print("  BİST ESv1 TARAMA — GÜNLÜK PERİYOT")
    print(f"  Tarih  : {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    print(f"  HTF    : {'AÇIK' if USE_HTF else 'KAPALI'}")
    print(f"  Hacim  : {'AÇIK' if USE_VOLUME else 'KAPALI'}")
    print(f"  Hisse  : {len(BIST_HISSELER)} adet")
    print("  ⭐ Son kapanan günlük mumda sinyal aranıyor")
    print("     → Ertesi gün açılışta giriş yapılabilir")
    print("="*60)

    al_listesi   = []
    hata_listesi = []
    toplam       = len(BIST_HISSELER)

    for idx, hisse in enumerate(BIST_HISSELER, 1):
        ticker = hisse + ".IS"
        print(f"  [{idx:3d}/{toplam}] {hisse:<10}", end=" ", flush=True)
        try:
            if USE_HTF and not htf_ok(ticker):
                print("— HTF engelledi")
                continue

            df = veri_cek(ticker, PERIOD_1D, INTERVAL)
            if df is None or len(df) < 30:
                print("⚠ Veri yok")
                hata_listesi.append(hisse)
                continue

            al, sat, close = sinyal_hesapla(df)

            if len(al) < 3:
                print("— Yetersiz veri")
                continue

            # Son kapanan mum (iloc[-1]) — günlük periyotta mum kapanmış olur
            # Tarama akşam yapıldığı için son mum kesinleşmiş
            son_al = bool(al.iloc[-1])
            son_sat = bool(sat.iloc[-1])

            if son_al:
                sinyal_tarihi = df.index[-1].strftime("%d.%m.%Y")
                sinyal_fiyat  = round(float(close.iloc[-1]), 2)

                al_listesi.append({
                    "Hisse"          : hisse,
                    "Kapanış Fiyatı" : sinyal_fiyat,
                    "Sinyal Tarihi"  : sinyal_tarihi,
                    "Not"            : "Ertesi gün açılışta giriş"
                })
                print(f"✅ AL — {sinyal_fiyat} ₺  ({sinyal_tarihi})")
            elif son_sat:
                print("-- SAT")
            else:
                print("— Sinyal yok")

        except Exception as e:
            print(f"✗ Hata: {e}")
            hata_listesi.append(hisse)

    # ─────────────────────────────────────────────
    # SONUÇLAR
    # ─────────────────────────────────────────────
    print("\n" + "="*60)
    print(f"  AL SİNYALİ VEREN HİSSELER ({len(al_listesi)} adet)")
    print(f"  → Yarın açılışta giriş yapılabilir")
    print("="*60)
    if al_listesi:
        for h in al_listesi:
            print(f"  {h['Hisse']:<10} {h['Kapanış Fiyatı']:>10.2f} ₺   {h['Sinyal Tarihi']}")
    else:
        print("  Sinyal veren hisse bulunamadı.")

    if al_listesi:
        dosya = f"bist_al_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        pd.DataFrame(al_listesi).to_excel(dosya, index=False)
        print(f"\n  📊 Excel kaydedildi: {dosya}")

    if hata_listesi:
        print(f"\n  ⚠ Veri alınamayan: {len(hata_listesi)} hisse")

    print("="*60 + "\n")
    input("  Çıkmak için Enter'a basın...")

if __name__ == "__main__":
    tara()

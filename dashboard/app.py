from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Titik Panas Karhutla Indonesia", layout="wide")
DATA = Path(__file__).parent / "data"
BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
BLN = [b[:3] for b in BULAN]

@st.cache_data
def muat(nama):
    return pd.read_parquet(DATA / f"{nama}.parquet")

def angka(n):
    n = float(n)
    if n >= 1e6: return f"{n / 1e6:.1f} juta".replace(".", ",")
    if n >= 1e3: return f"{n / 1e3:.0f} ribu"
    return f"{n:.0f}"

def persen(x):
    return f"{x * 100:.0f}%"

prov_bulan, kab_tahun, grid = muat("prov_bulan"), muat("kab_tahun"), muat("grid_bulan")
try:
    luas = muat("luas")
except Exception:
    luas = None
klaster, tipologi, risiko, evaluasi = muat("klaster"), muat("tipologi"), muat("risiko"), muat("evaluasi")
try:
    import json
    _meta = json.loads((DATA / "meta.json").read_text())
    PAKAI_HUJAN, MODEL_AWAL = _meta.get("pakai_hujan", False), _meta.get("model_awal", "")
except Exception:
    PAKAI_HUJAN, MODEL_AWAL = False, ""

st.sidebar.title("Titik Panas Karhutla")
halaman = st.sidebar.radio("Pilih halaman", ["Beranda", "Kapan terjadi?", "Di mana terjadi?", "Luas terbakar", "Daerah rawan", "Prakiraan minggu depan", "Tentang data"])
tahun_semua = sorted(prov_bulan["tahun"].unique())
rentang = st.sidebar.select_slider("Tahun yang ditampilkan", options=tahun_semua, value=(tahun_semua[0], tahun_semua[-1]))
pilih_prov = st.sidebar.multiselect("Batasi ke provinsi tertentu (kosong = semua)", sorted(prov_bulan["provinsi"].unique()))
st.sidebar.info("**Titik panas** = lokasi yang dilihat satelit lebih panas dari sekitarnya, kemungkinan ada api. "
                "Ini bukan jumlah kebakaran yang pasti. Penjelasan lengkap di halaman *Tentang data*.")

def saring(d):
    d = d[d["tahun"].between(*rentang)]
    return d[d["provinsi"].isin(pilih_prov)] if pilih_prov else d

pb, kt = saring(prov_bulan), saring(kab_tahun)
if pb.empty:
    st.warning("Tidak ada data untuk pilihan ini. Ubah tahun atau provinsi di panel kiri."); st.stop()

per_tahun = pb.groupby("tahun")["n_titik"].sum()
per_bulan = pb.groupby("bulan")["n_titik"].sum().reindex(range(1, 13), fill_value=0)
total = int(per_tahun.sum())
jendela = [per_bulan.iloc[i:i + 3].sum() for i in range(10)]            # 3 bulan berurutan dengan titik terbanyak
i3 = int(np.argmax(jendela)); porsi3 = jendela[i3] / max(per_bulan.sum(), 1)
prov_tot = pb.groupby("provinsi")["n_titik"].sum().sort_values(ascending=False)
kab_tot = kt.groupby(["kabupaten", "provinsi"], as_index=False)["n_titik"].sum().sort_values("n_titik", ascending=False)

# ------------------------------------------------------------------ BERANDA
if halaman == "Beranda":
    st.title("Titik Panas Karhutla Indonesia")
    st.write(f"Data satelit tahun **{rentang[0]}–{rentang[1]}**. Halaman ini merangkum **kapan** dan **di mana** titik panas paling banyak muncul.")
    k1, k2, k3 = st.columns(3)
    k1.metric("Total titik panas", angka(total))
    k2.metric("Tahun terparah", f"{int(per_tahun.idxmax())}"); k2.caption(f"{angka(per_tahun.max())} titik panas")
    k3.metric("Bulan paling rawan", f"{BLN[i3]}–{BLN[i3 + 2]}"); k3.caption(f"{persen(porsi3)} dari semua titik ({BULAN[i3]} sampai {BULAN[i3 + 2]})")

    st.subheader("Temuan utama")
    median = per_tahun.median()
    if len(per_tahun) >= 3 and median > 0:
        st.info(f"**Satu tahun bisa jauh lebih parah dari yang lain.** Tahun {int(per_tahun.idxmax())} mencatat {angka(per_tahun.max())} titik panas, "
                f"sekitar {per_tahun.max() / median:.0f} kali lipat tahun yang biasa ({angka(median)} titik).")
    st.info(f"**Musim rawan jelas.** Sekitar {persen(porsi3)} titik panas muncul hanya dalam 3 bulan: {BULAN[i3]} sampai {BULAN[i3 + 2]}.")
    if len(prov_tot) and len(kab_tot):
        top3 = prov_tot.head(3)
        st.info(f"**Terkonsentrasi di beberapa daerah.** Tiga provinsi teratas ({', '.join(top3.index)}) menyumbang {persen(top3.sum() / total)} dari semua titik. "
                f"Kabupaten teratas: {kab_tot.iloc[0]['kabupaten']} ({kab_tot.iloc[0]['provinsi']}).")
    d = per_tahun.reset_index(); d.columns = ["Tahun", "Titik panas"]
    d["Kategori"] = np.where(d["Titik panas"] >= 2 * median, "Sangat parah (≥ 2× biasa)", "Biasa")
    fig = px.bar(d, x="Tahun", y="Titik panas", color="Kategori", title="Jumlah titik panas per tahun",
                 color_discrete_map={"Sangat parah (≥ 2× biasa)": "#b30000", "Biasa": "#9ecae1"})
    fig.update_xaxes(type="category"); st.plotly_chart(fig, width="stretch")

# ------------------------------------------------------------------ KAPAN
elif halaman == "Kapan terjadi?":
    st.title("Kapan titik panas paling banyak?")
    st.info(f"**Puncaknya di {BULAN[i3]}–{BULAN[i3 + 2]}.** {persen(porsi3)} titik panas muncul di tiga bulan ini. "
            "Di luar musim itu jumlahnya jauh lebih sedikit.")
    rata = (pb.groupby(["tahun", "bulan"])["n_titik"].sum().groupby("bulan").mean().reindex(range(1, 13), fill_value=0)).reset_index()
    rata.columns = ["bulan", "rata"]; rata["Bulan"] = [BLN[b - 1] for b in rata["bulan"]]
    rata["Musim"] = np.where(rata["bulan"].between(i3 + 1, i3 + 3), "Puncak", "Lainnya")
    fig = px.bar(rata, x="Bulan", y="rata", color="Musim", title="Rata-rata titik panas per bulan (dihitung dari semua tahun terpilih)",
                 labels={"rata": "Titik panas"}, category_orders={"Bulan": BLN}, color_discrete_map={"Puncak": "#b30000", "Lainnya": "#9ecae1"})
    st.plotly_chart(fig, width="stretch")

    st.subheader("Bulan puncak tiap provinsi")
    pm = pb.groupby(["provinsi", "bulan"])["n_titik"].sum().reset_index()
    idx = pm.groupby("provinsi")["n_titik"].idxmax()
    tabel = pm.loc[idx].assign(**{"Bulan puncak": lambda x: [BULAN[b - 1] for b in x["bulan"]]})
    tabel = tabel.merge(prov_tot.rename("Total titik").reset_index(), on="provinsi").sort_values("Total titik", ascending=False)
    st.caption("Diurutkan dari provinsi dengan titik panas terbanyak. Provinsi bertitik sedikit sebaiknya tidak ditafsirkan.")
    st.dataframe(tabel[["provinsi", "Bulan puncak", "Total titik"]].rename(columns={"provinsi": "Provinsi"}).head(15), hide_index=True, width="stretch")

    with st.expander("Lihat tahun demi tahun (kalender panas)"):
        pivot = pb.groupby(["tahun", "bulan"])["n_titik"].sum().unstack(fill_value=0).reindex(columns=range(1, 13), fill_value=0)
        pivot.columns = BLN
        st.plotly_chart(px.imshow(pivot, aspect="auto", color_continuous_scale="YlOrRd", labels=dict(x="Bulan", y="Tahun", color="Titik panas"),
                                  title="Makin gelap = makin banyak titik panas"), width="stretch")

# ------------------------------------------------------------------ DI MANA
elif halaman == "Di mana terjadi?":
    st.title("Di mana titik panas paling banyak?")
    if len(prov_tot) and len(kab_tot):
        st.info(f"**{prov_tot.index[0]}** paling banyak ({angka(prov_tot.iloc[0])} titik, {persen(prov_tot.iloc[0] / total)} dari total). "
                f"Kabupaten teratas: **{kab_tot.iloc[0]['kabupaten']}**. Sepuluh kabupaten teratas menyumbang {persen(kab_tot.head(10)['n_titik'].sum() / total)} dari semua titik.")
    pilihan = st.radio("Bulan yang ditampilkan di peta", ["Musim rawan (3 bulan puncak)", "Semua bulan"], horizontal=True)
    b1, b2 = (i3 + 1, i3 + 3) if pilihan.startswith("Musim") else (1, 12)
    g = grid[grid["tahun"].between(*rentang) & grid["bulan"].between(b1, b2)].groupby(["id_sel", "lat", "lon"], as_index=False)["n_titik"].sum()
    g = g.rename(columns={"n_titik": "Titik panas"})
    if g.empty:
        st.info("Tidak ada data pada pilihan ini.")
    else:
        fig = px.scatter_map(g, lat="lat", lon="lon", size="Titik panas", color="Titik panas", color_continuous_scale="YlOrRd",
                             size_max=18, zoom=3.5, height=560, map_style="carto-positron", title="Makin besar dan gelap = makin banyak titik panas")
        st.plotly_chart(fig, width="stretch")
    c1, c2 = st.columns(2)
    with c1:
        p = prov_tot.head(10).sort_values().reset_index(); p.columns = ["Provinsi", "Titik panas"]
        st.plotly_chart(px.bar(p, x="Titik panas", y="Provinsi", orientation="h", title="10 provinsi teratas"), width="stretch")
    with c2:
        st.markdown("**10 kabupaten teratas**")
        t = kab_tot.head(10).copy(); t["Porsi dari total"] = (t["n_titik"] / total).map(persen)
        st.dataframe(t.rename(columns={"kabupaten": "Kabupaten/Kota", "provinsi": "Provinsi", "n_titik": "Titik panas"}), hide_index=True, width="stretch")
    st.subheader("Cari kabupaten/kota")
    pilih = st.selectbox("Kabupaten/Kota", sorted(kt["kabupaten"].unique()))
    s = kt[kt["kabupaten"] == pilih].groupby("tahun", as_index=False)["n_titik"].sum().rename(columns={"tahun": "Tahun", "n_titik": "Titik panas"})
    fig = px.bar(s, x="Tahun", y="Titik panas", title=f"{pilih}: titik panas per tahun"); fig.update_xaxes(type="category")
    st.plotly_chart(fig, width="stretch")

# ------------------------------------------------------------------ LUAS TERBAKAR
elif halaman == "Luas terbakar":
    st.title("Berapa luas lahan yang terbakar?")
    if luas is None or luas.empty:
        st.info("Data luas terbakar belum tersedia. Jalankan sel ekspor luas di notebook, lalu muat ulang halaman ini.")
        st.stop()
    JAKARTA_HA = 66000
    lt = luas[luas["tahun"].between(*rentang)]
    if pilih_prov:
        lt = lt[lt["provinsi"].isin(pilih_prov)]
    titik = prov_bulan.groupby(["tahun", "provinsi"], as_index=False)["n_titik"].sum()
    m = lt.merge(titik, on=["tahun", "provinsi"], how="left").fillna({"n_titik": 0})
    if m.empty:
        st.warning("Tidak ada data luas untuk pilihan ini. Data luas tersedia untuk tahun " f"{int(luas['tahun'].min())}–{int(luas['tahun'].max())}."); st.stop()
    st.write("Titik panas hanya menandai *ada api*. Halaman ini menambahkan **luas lahan yang terbakar** (hektare) dari data resmi SiPongi, "
             "supaya terlihat apakah banyak titik panas memang berarti lahan yang terbakar juga luas.")
    st.caption(f"Data luas tersedia untuk {int(m['tahun'].min())}–{int(m['tahun'].max())}. Satu hektare kira-kira satu lapangan sepak bola.")
    tot = m.groupby("tahun").agg(luas_ha=("luas_ha", "sum"), n_titik=("n_titik", "sum"))
    th_max = int(tot["luas_ha"].idxmax())
    k1, k2, k3 = st.columns(3)
    k1.metric("Total luas terbakar", f"{angka(tot['luas_ha'].sum())} ha")
    k2.metric("Tahun terluas", f"{th_max}"); k2.caption(f"{angka(tot['luas_ha'].max())} hektare")
    pt_ = m.groupby("provinsi")["luas_ha"].sum().sort_values(ascending=False)
    k3.metric("Provinsi terluas", pt_.index[0]); k3.caption(f"{angka(pt_.iloc[0])} hektare ({persen(pt_.iloc[0] / pt_.sum())} dari total)")

    st.subheader("Temuan utama")
    st.info(f"**Tahun terparah: {th_max}.** Sekitar {angka(tot['luas_ha'].max())} hektare terbakar, kira-kira "
            f"{tot['luas_ha'].max() / JAKARTA_HA:.0f} kali luas DKI Jakarta (±66 ribu hektare).")
    if len(tot) >= 4:
        r = tot["luas_ha"].corr(tot["n_titik"], method="spearman")
        if r >= 0.7:
            st.info("**Banyak titik panas biasanya berarti lahan terbakar luas.** Tahun dengan titik panas terbanyak umumnya juga tahun dengan lahan terbakar terluas, "
                    "jadi titik panas cukup berguna sebagai petunjuk tingkat keparahan satu tahun.")
        elif r >= 0.4:
            st.info("**Hubungannya ada, tapi tidak kuat.** Tahun dengan banyak titik panas cenderung punya lahan terbakar lebih luas, tetapi ada banyak pengecualian.")
        else:
            st.warning("**Jumlah titik panas kurang mencerminkan luas terbakar** pada data ini. Jangan memakai titik panas sebagai pengganti luas.")
    n_min = 500
    rasio = m[m["n_titik"] >= n_min].assign(ha_per_titik=lambda x: x["luas_ha"] / x["n_titik"])
    if len(rasio) >= 5:
        hi, lo = rasio.loc[rasio["ha_per_titik"].idxmax()], rasio.loc[rasio["ha_per_titik"].idxmin()]
        st.info(f"**Satu titik panas bisa berarti luas yang sangat berbeda.** Di {hi['provinsi']} ({int(hi['tahun'])}) rata-rata {hi['ha_per_titik']:.0f} hektare per titik, "
                f"sedangkan di {lo['provinsi']} ({int(lo['tahun'])}) hanya {lo['ha_per_titik']:.1f} hektare per titik. "
                "Karena itu angka titik panas sebaiknya dipakai untuk membandingkan, bukan untuk menghitung luas.")

    c1, c2 = st.columns(2)
    d1 = tot.reset_index()
    with c1:
        f = px.bar(d1, x="tahun", y="n_titik", title="Titik panas per tahun", labels={"tahun": "Tahun", "n_titik": "Titik panas"}, color_discrete_sequence=["#9ecae1"])
        f.update_xaxes(type="category"); st.plotly_chart(f, width="stretch")
    with c2:
        f = px.bar(d1, x="tahun", y="luas_ha", title="Luas terbakar per tahun (hektare)", labels={"tahun": "Tahun", "luas_ha": "Hektare"}, color_discrete_sequence=["#b30000"])
        f.update_xaxes(type="category"); st.plotly_chart(f, width="stretch")

    st.subheader("Provinsi dengan lahan terbakar terluas")
    tp = m.groupby("provinsi").agg(luas_ha=("luas_ha", "sum"), n_titik=("n_titik", "sum")).sort_values("luas_ha", ascending=False).head(10).reset_index()
    tp["Hektare per titik"] = np.where(tp["n_titik"] > 0, tp["luas_ha"] / tp["n_titik"].replace(0, np.nan), np.nan).round(1)
    tp["Porsi dari total"] = (tp["luas_ha"] / m["luas_ha"].sum()).map(persen)
    st.dataframe(tp.assign(luas_ha=tp["luas_ha"].round(0), n_titik=tp["n_titik"].round(0))
                 .rename(columns={"provinsi": "Provinsi", "luas_ha": "Luas terbakar (ha)", "n_titik": "Titik panas"}), hide_index=True, width="stretch")

    with st.expander("Lihat hubungan titik panas dan luas per provinsi dan tahun"):
        sc = m[(m["n_titik"] > 0) & (m["luas_ha"] > 0)].copy()
        sc["tahun"] = sc["tahun"].astype(str)
        st.plotly_chart(px.scatter(sc, x="n_titik", y="luas_ha", color="tahun", hover_name="provinsi", log_x=True, log_y=True,
                                   labels={"n_titik": "Titik panas (skala log)", "luas_ha": "Hektare (skala log)", "tahun": "Tahun"},
                                   title="Tiap titik = satu provinsi pada satu tahun. Makin ke kanan atas = makin parah"), width="stretch")
    st.caption("Sumber: SIPONGI KEMENHUT (indikasi luas kebakaran, perkiraan dari citra satelit Landsat 8 yang dicocokkan dengan titik panas, pengecekan lapangan, dan laporan pemadaman). "
               "Provinsi hasil pemekaran Papua digabung ke provinsi induknya agar sesuai dengan batas wilayah.")

# ------------------------------------------------------------------ DAERAH RAWAN
elif halaman == "Daerah rawan":
    st.title("Daerah rawan")
    n_tahun = len(tahun_semua)
    st.caption(f"Halaman ini memakai seluruh tahun ({tahun_semua[0]}–{tahun_semua[-1]}), tidak mengikuti pilihan tahun di panel kiri.")
    st.subheader("Seberapa sering kabupaten terbakar?")
    st.write("Kabupaten dikelompokkan otomatis menurut jumlah titik panas rata-rata per tahun dan seberapa sering mereka terkena. "
             "Pengelompokan ini membantu menentukan jenis penanganan: daerah *rawan tinggi* perlu pencegahan rutin, daerah yang jarang terbakar cukup dipantau.")
    tp = tipologi.assign(rata=np.expm1(tipologi["log_rata_tahunan"]))
    urut = ["Rawan tinggi", "Rawan sedang", "Rawan rendah", "Jarang terbakar"]
    ada = [u for u in urut if u in set(tp["tipologi"])] + sorted(set(tp["tipologi"]) - set(urut))
    kol = st.columns(len(ada))
    for c, nm in zip(kol, ada):
        x = tp[tp["tipologi"] == nm]
        c.metric(nm, f"{len(x)}")
        c.caption(f"kabupaten/kota. Rata-rata {angka(x['rata'].mean())} titik/tahun per kabupaten. Berapi di {x['porsi_tahun_berapi'].mean() * n_tahun:.0f} dari {n_tahun} tahun.")
    lihat = st.selectbox("Lihat daftar kabupaten", ada)
    daftar = tp[tp["tipologi"] == lihat].sort_values("rata", ascending=False)
    st.dataframe(daftar.assign(**{"Rata-rata titik/tahun": daftar["rata"].round(0)})[["kabupaten", "provinsi", "Rata-rata titik/tahun"]]
                 .rename(columns={"kabupaten": "Kabupaten/Kota", "provinsi": "Provinsi"}), hide_index=True, width="stretch")

    st.subheader("Kawasan api terbesar tiap tahun")
    st.write("Kawasan = kumpulan titik panas yang saling berdekatan (dalam kira-kira 10 km) pada musim rawan (Agustus–Oktober).")
    th = st.selectbox("Tahun", sorted(klaster["tahun"].unique(), reverse=True))
    k = klaster[klaster["tahun"] == th].nlargest(10, "n_titik")
    fig = px.scatter_map(k, lat="lat", lon="lon", size="n_titik", color="n_titik", color_continuous_scale="YlOrRd", zoom=3.5, height=480,
                         size_max=30, map_style="carto-positron", hover_name="kabupaten", labels={"n_titik": "Titik panas"})
    st.plotly_chart(fig, width="stretch")
    st.dataframe(k.assign(**{"Perkiraan titik panas": k["n_titik"].round(0)})[["kabupaten", "provinsi", "Perkiraan titik panas"]]
                 .rename(columns={"kabupaten": "Sekitar kabupaten", "provinsi": "Provinsi"}), hide_index=True, width="stretch")
    st.caption("Jumlah adalah perkiraan (dikoreksi bila data banyak sehingga hanya sebagian yang diproses). Nama daerah = kabupaten terdekat dari pusat kawasan.")

# ------------------------------------------------------------------ PRAKIRAAN
elif halaman == "Prakiraan minggu depan":
    st.title("Prakiraan area rawan minggu depan")
    st.warning("Ini **hasil model statistik**, bukan peringatan resmi dari BMKG atau KLHK. Pakai untuk membantu menentukan prioritas pemantauan.")
    st.write("Setiap minggu, model menilai tiap area (kotak sekitar 50 × 50 km) dari pola beberapa minggu terakhir dan musim: "
             "**seberapa mungkin area itu muncul titik panas pada minggu berikutnya?**")
    u = evaluasi[evaluasi["tahun_uji"] == evaluasi["tahun_uji"].max()].set_index("model")
    a, b, c = u.loc["LightGBM + kalibrasi", "presisi_at_50"], u.loc["Klimatologi", "presisi_at_50"], u.loc["Persistence", "presisi_at_50"]
    st.subheader("Seberapa bisa dipercaya?")
    st.info(f"Diuji pada tahun **{int(u['tahun_uji'].iloc[0])}** (data yang tidak dipakai saat model belajar). Tiap minggu diambil **50 area** dengan risiko tertinggi. "
            f"Rata-rata **{persen(a)}** dari 50 area itu memang muncul titik panas minggu berikutnya. "
            f"Sebagai pembanding: menebak hanya dari pola musim → {persen(b)}; menebak “minggu depan sama dengan minggu ini” → {persen(c)}.")
    unggul = a - max(b, c)
    if unggul < 0.05:
        st.warning("Selisih dengan tebakan pembanding terbaik kecil, jadi model ini baru sedikit menambah ketepatan.")
    else:
        st.success(f"Model unggul sekitar **{unggul * 100:.0f} poin persen** dibanding tebakan pembanding terbaik. Keunggulannya nyata tetapi bukan mutlak: "
                   "kebakaran di area yang sama dari minggu ke minggu sudah menjadi petunjuk yang kuat.")
    ket = evaluasi[evaluasi["model"].isin(["LightGBM + kalibrasi", "Klimatologi"])].pivot(index="tahun_uji", columns="model", values="presisi_at_50")
    if len(ket) > 1:
        st.write("**Bagaimana di tahun lain?** (tahun parah biasanya lebih sulit)")
        st.dataframe(ket.rename(columns={"LightGBM + kalibrasi": "Model", "Klimatologi": "Tebakan pola musim"}).map(persen)
                     .rename_axis("Tahun uji").reset_index(), hide_index=True, width="stretch")
    st.subheader("Simulasi per minggu")
    st.caption("Ini simulasi di masa lalu: minggu yang dipilih disembunyikan dari model, lalu prakiraannya dicocokkan dengan kenyataan.")
    minggu = sorted(risiko["minggu_target"].unique())
    banyak = risiko.assign(t=risiko["skor"] >= 0.5).groupby("minggu_target")["t"].sum()
    pilih_m = st.select_slider("Minggu yang diprakirakan (tanggal Senin)", options=minggu, value=banyak.idxmax(),
                               format_func=lambda x: pd.Timestamp(x).strftime("%d %b %Y"))
    r = risiko[risiko["minggu_target"] == pilih_m].copy()
    r["Tingkat risiko"] = pd.cut(r["skor"], [-0.01, 0.25, 0.5, 0.75, 1.01], labels=["Rendah", "Sedang", "Tinggi", "Sangat tinggi"])
    k1, k2 = st.columns(2)
    k1.metric("Area berisiko tinggi atau sangat tinggi", int((r["skor"] >= 0.5).sum()))
    k2.metric("Area yang kenyataannya muncul titik panas", int(r["terjadi"].sum()))
    tampil = r[r["skor"] >= 0.25]
    if tampil.empty:
        st.info("Minggu ini tidak ada area dengan risiko sedang ke atas.")
    else:
        fig = px.scatter_map(tampil, lat="lat", lon="lon", color="Tingkat risiko", zoom=3.5, height=520, map_style="carto-positron",
                             hover_name="kabupaten", category_orders={"Tingkat risiko": ["Sedang", "Tinggi", "Sangat tinggi"]},
                             color_discrete_map={"Sedang": "#fdae6b", "Tinggi": "#e6550d", "Sangat tinggi": "#a50f15"})
        fig.update_traces(marker=dict(size=14)); st.plotly_chart(fig, width="stretch")
    top = r.nlargest(10, "skor").assign(**{"Kenyataan": lambda x: np.where(x["terjadi"] == 1, "Ada titik panas", "Tidak ada")})
    st.markdown("**10 area dengan risiko tertinggi minggu ini**")
    st.dataframe(top.assign(Risiko=top["skor"].map(persen))[["kabupaten", "provinsi", "Tingkat risiko", "Risiko", "Kenyataan"]]
                 .rename(columns={"kabupaten": "Sekitar kabupaten", "provinsi": "Provinsi"}), hide_index=True, width="stretch")
    with st.expander("Untuk yang ingin tahu lebih detail (istilah teknis)"):
        st.write("PR-AUC dan Brier skill score (BSS) adalah ukuran ketepatan standar. Presisi@50 adalah persentase dari 50 area teratas yang benar-benar berapi.")
        st.dataframe(evaluasi, hide_index=True, width="stretch")

# ------------------------------------------------------------------ TENTANG
else:
    st.title("Tentang data dan cara membacanya")
    st.markdown("""
**Dari mana datanya?** Satelit NASA (instrumen VIIRS, resolusi 375 m) memotret Indonesia beberapa kali sehari dan menandai lokasi yang jauh lebih panas dari sekitarnya.
Lokasi itu disebut *titik panas*. Batas kabupaten/kota dari data batas administrasi, sehingga setiap titik bisa dicocokkan dengan daerahnya.

**Apakah titik panas = jumlah kebakaran?** Tidak. Satu kebakaran besar bisa menghasilkan banyak titik, sedangkan kebakaran kecil atau yang tertutup awan/asap bisa tidak terdeteksi.
Karena itu gunakan angka di sini untuk **membandingkan** (tahun, bulan, daerah), bukan untuk menghitung jumlah kejadian atau luas lahan terbakar.

**Kenapa ada titik “malam”?** Satelit melintas pada jam yang tetap, jadi yang bisa dibandingkan hanya siang vs malam. Ini bukan jam terjadinya kebakaran.

**Apa arti “tingkat risiko”?** Itu perkiraan peluang sebuah area muncul titik panas minggu depan: rendah (<25%), sedang (25–50%), tinggi (50–75%), sangat tinggi (>75%).
Skornya bisa terlalu yakin di ujung atas, jadi baca sebagai urutan prioritas, bukan kepastian.

**Batasan yang perlu diingat**
- Batas wilayah mengikuti versi tahun 2020, sehingga pemekaran wilayah sesudahnya (misalnya di Papua) belum tercermin. Data luas terbakar provinsi baru di Papua digabung ke provinsi induknya.
- Luas terbakar (halaman *Luas terbakar*) berasal dari SIPONGI KEMENHUT dan berupa **indikasi** dari citra satelit, bukan pengukuran pasti. Data tahun 2025 belum dipakai karena tampak belum lengkap.
- {hujan}
- Model prakiraan dilatih dengan data mulai tahun {model_awal}, sedangkan halaman lain memakai seluruh tahun yang tersedia.
- Hasil ini belum diuji secara resmi dan bukan peringatan dini yang sah.
""".replace("{model_awal}", MODEL_AWAL or "awal data").replace("{hujan}", "Model memakai data curah hujan bulanan (hujan 1 dan 3 bulan terakhir) sebagai petunjuk kekeringan, tetapi bukan hujan harian. Pada pengujian, tambahan ini hanya sedikit mengubah ketepatan: pola kebakaran beberapa minggu terakhir tetap petunjuk terkuat." if PAKAI_HUJAN else "Model belum memakai data curah hujan, sehingga tebakannya sebagian besar mengandalkan pola musim dan kejadian beberapa minggu terakhir."))


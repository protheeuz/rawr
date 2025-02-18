import os
import cv2
import numpy as np
import pickle
from tensorflow.keras.preprocessing import image
from tensorflow.keras.models import load_model
import base64

# Muat model CNN untuk deteksi kanker
base_dir = os.path.abspath(os.path.dirname(__file__))
cnn_model_path = os.path.join(base_dir, '..', 'models', 'model_kanker_payudara.keras')
label_pickle_path = os.path.join(base_dir, '..', 'models', 'label_mapping.pkl')

# Muat label kelas dari pickle
with open(label_pickle_path, "rb") as f:
    label_mapping = pickle.load(f)

# Muat model tanpa optimizer, untuk prediksi
cnn_model = load_model(cnn_model_path, compile=False)

def predict_with_confidence(img_path, user_email):
    """
    Fungsi ini untuk deteksi gambar pakai model CNN dan kasih tahu hasilnya dalam bentuk gambar dengan label dan probabilitas.
    """
    # Membaca gambar dengan OpenCV
    img_cv = cv2.imread(img_path)  # Baca gambar dari path yang dikasih
    if img_cv is None:  # Cek kalau gambar gagal dibaca
        print("Gagal memuat gambar untuk prediksi")  # Kalau gagal, kasih tahu ke console
        return None, None, None  # Kembalikan None untuk semua hasil

    # Resize gambar ke ukuran yang diminta model
    img_resized = cv2.resize(img_cv, (224, 224))  # Resize gambar jadi 224x224 supaya cocok dengan input model

    # Preprocessing gambar
    img_array = image.img_to_array(img_resized) / 255.0  # Ubah gambar jadi array dan normalisasi (0-1)
    img_array = np.expand_dims(img_array, axis=0)  # Tambahin dimensi batch (model butuh batch input)

    # Lakukan prediksi
    prediksi = cnn_model.predict(img_array)  # Prediksi dengan model CNN
    probabilitas_kanker = prediksi[0][0]  # Ambil probabilitas untuk kelas kanker (biasanya di index pertama)

    # Tentukan label dari pickle
    label = label_mapping[1] if probabilitas_kanker >= 0.5 else label_mapping[0]  # Tentuin label, kalau >= 50% ya kanker
    warna = (0, 0, 255) if probabilitas_kanker >= 0.5 else (0, 255, 0)  # Tentuin warna, merah untuk kanker, hijau untuk normal

    tinggi, lebar, _ = img_cv.shape  # Ambil ukuran gambar (tinggi, lebar) buat gambar persegi panjang
    padding = 100  # Margin atau jarak sekitar 100px

    # Gambar persegi panjang
    img_cv = cv2.rectangle(  # Gambar persegi panjang untuk frame di gambar
        img_cv,
        (padding, padding),  # Posisi kiri atas persegi panjang
        (lebar - padding, tinggi - padding),  # Posisi kanan bawah persegi panjang
        warna,  # Warna yang sesuai (merah/hijau)
        5  # Ketebalan garis persegi panjang
    )

    # Tambahkan teks label
    img_cv = cv2.putText(  # Tambahin teks ke gambar (label + probabilitas)
        img_cv,
        f"{label} ({probabilitas_kanker:.2%})",  # Teks yang muncul di gambar (label dan probabilitas dalam persen)
        (50, tinggi - 60),  # Posisi teks di gambar
        cv2.FONT_HERSHEY_SIMPLEX,  # Tipe font
        1,  # Ukuran font
        warna,  # Warna teks
        3,  # Ketebalan font
        cv2.LINE_AA  # Tipenya (menghaluskan teks)
    )

    # Path untuk menyimpan gambar hasil deteksi
    output_img_path = os.path.join(base_dir, 'static', 'assets', 'img', 'detections', f"{user_email}_detected_image.png")
    cv2.imwrite(output_img_path, img_cv)  # Simpan gambar yang sudah diberi label ke path yang ditentukan

    # Konversi ke base64 untuk tampilan
    _, buffer = cv2.imencode('.png', img_cv)  # Encode gambar ke format PNG
    img_base64 = base64.b64encode(buffer).decode('utf-8')  # Ubah gambar jadi format base64 supaya bisa ditampilkan di web

    return label, probabilitas_kanker * 100, img_base64, output_img_path  # Kembalikan hasil (label, probabilitas, gambar base64, path gambar)
import os
import cv2
import numpy as np
from tensorflow.keras.preprocessing import image
from tensorflow.keras.models import load_model
import base64

# Muat model CNN untuk deteksi kanker
base_dir = os.path.abspath(os.path.dirname(__file__))
cnn_model_path = os.path.join(base_dir, '..', 'models', 'model_kanker_payudara.keras')

# Simpan gambar dengan nama unik
output_img_path = os.path.join(base_dir, 'static', 'assets', 'img', 'detections', 'detected_image.png')
print(f"Image saved at: {output_img_path}")
if os.path.exists(output_img_path):
    print(f"Image exists: {output_img_path}")
else:
    print(f"Image not found at: {output_img_path}")


if not os.path.exists(os.path.dirname(output_img_path)):
    os.makedirs(os.path.dirname(output_img_path))
    print(f"Directory created: {os.path.dirname(output_img_path)}")

# Muat model tanpa optimizer, untuk prediksi
cnn_model = load_model(cnn_model_path, compile=False)

def predict_with_confidence(img_path, user_email):
    """
    Fungsi untuk melakukan deteksi dengan model CNN dan menampilkan hasilnya dengan visualisasi.
    """
    # Membaca gambar dengan OpenCV
    img_cv = cv2.imread(img_path)
    if img_cv is None:
        print("Gagal memuat gambar untuk prediksi")
        return None, None, None

    # Resize gambar ke ukuran yang diminta model
    img_resized = cv2.resize(img_cv, (224, 224))

    # Preprocessing gambar
    img_array = image.img_to_array(img_resized) / 255.0  # Normalisasi
    img_array = np.expand_dims(img_array, axis=0)  # Tambahkan dimensi batch

    # Lakukan prediksi
    prediksi = cnn_model.predict(img_array)
    probabilitas_kanker = prediksi[0][0]  # Ambil probabilitas kelas 1 (kanker)

    # Tentukan label dan warna berdasarkan prediksi
    if probabilitas_kanker >= 0.5:
        label = "Kanker (Ganas)"
        warna = (0, 0, 255)  # Merah untuk kanker
    else:
        label = "Tidak Kanker (Jinak)"
        warna = (0, 255, 0)  # Hijau untuk non-kanker

    tinggi, lebar, _ = img_cv.shape
    padding = 100

    # Gambar persegi panjang
    img_cv = cv2.rectangle(
        img_cv,
        (padding, padding),
        (lebar - padding, tinggi - padding),
        warna,
        5
    )

    # Tambahkan teks label
    img_cv = cv2.putText(
        img_cv,
        f"{label} ({probabilitas_kanker:.2%})",
        (50, tinggi - 60),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        warna,
        3,
        cv2.LINE_AA
    )

    # Simpan gambar dengan nama unik berdasarkan email
    output_img_path = os.path.join(base_dir, 'static', 'assets', 'img', 'detections', f"{user_email}_detected_image.png")
    cv2.imwrite(output_img_path, img_cv)

    # Konversi ke base64 untuk tampilan
    _, buffer = cv2.imencode('.png', img_cv)
    img_base64 = base64.b64encode(buffer).decode('utf-8')

    return label, probabilitas_kanker * 100, img_base64, output_img_path
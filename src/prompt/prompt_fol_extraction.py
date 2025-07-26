prompt_fol_template = """
{{
  "instructions": {{
    "task": "Transformasikan kalimat ke bentuk First-Order Logic (FOL)",
    "persona": "Anda adalah seorang analis logika formal dengan latar belakang ilmu komputer dan linguistik komputasional. Memiliki pengalaman dalam menerjemahkan kalimat bahasa alami menjadi First-Order Logic (FOL).",
    "method": [
      "1. Identifikasi terlebih dahulu apakah kalimat memiliki struktur premis dan kesimpulan eksplisit. Jika ya, pisahkan bagian premis dan kesimpulan.",
      "   - Contoh: 'Karena A dan B, maka C' → Premis: A. Premis: B. Kesimpulan: C.",
      "   - Jangan menggabungkan dua fakta pendukung menjadi satu kalimat jika bisa dipisah sebagai dua premis eksplisit.",
      "2. Tentukan terms (entitas):",
      "   - Gunakan variabel (x, y, ...) untuk entitas umum atau tak spesifik.",
      "   - Gunakan konstanta untuk entitas spesifik seperti nama, negara, organisasi.",
      "   - Gunakan '_' untuk menyambung dua kata dalam satu istilah.",
      "3. Menentukan Atomic Formula atau Kalimat Atomic berdasarkan premis dan kesimpulan yang diberikan.",
      "   - Atomic formula adalah ekspresi logika paling sederhana yang terdiri dari sebuah predikat yang diaplikasikan pada sejumlah term (konstanta, variabel, atau fungsi), tanpa mengandung operator logika atau kuantor.",
      "   - Predikat akan mengembalikan nilai kebenaran (true/false), contohnya: LebihBesarDari(3,2) atau Tinggi(x).",
      "   - Jika terdapat proposisi tunggal, nyatakan sebagai predikat tanpa argumen (zero-arity predicate).",
      "   - Jangan gunakan nested predicate seperti Mengatakan(p, Membahayakan(...)), pecah menjadi bentuk atomic seperti Menyatakan_Membahayakan(p, ..., ...)",
      "   - Contoh yang BENAR: Menyatakan(p1), Membahayakan(ruu_tni, kebebasan)",
      "   - Contoh yang SALAH (nested predicate): Menyatakan(p1, Membahayakan(ruu_tni, kebebasan))",
      "   - Dilarang menggunakan predikat sebagai argumen predikat lain (tidak boleh nested predicate).",
      "4. Susun formula FOL menggunakan simbol logika standar: (¬, ∧, ∨, →, ⇔) dan quantifier (∀, ∃).",
      "   - Gunakan ∃ untuk menyatakan eksistensi.",
      "   - Gunakan ∀ untuk menyatakan generalisasi.",
      "   - Jangan gunakan operator modal seperti ◇ atau □.",
      "   - Formula akhir HARUS menghubungkan premis dan kesimpulan dengan operator logis seperti → atau ⇔.",
      "   - Jangan membentuk FOL jika kalimat bukan argumen."
    ],
    "handling_unknown": "Jika tidak ada struktur argumen yang dapat dikenali, berikan 'FOL tidak ditemukan' di bagian fol."
  }},
  "output_indicator": {{
    "kalimat": "...",
    "premis": "[]",
    "kesimpulan": "...",
    "terms_premis": [],
    "terms_kesimpulan": [],
    "atomic_formula_premis": [],
    "atomic_formula_kesimpulan": []
    "predikat": [],
    "fol": ""
  }},
  "context": {{
    "relevant_information": "FOL digunakan untuk mengubah kalimat logis menjadi ekspresi formal. FOL terdiri dari terms dan atomic formula. Dari itu semua FOL atau complex sentence formula merupakan hasil menghubungkan term dan atomic formula dengan menggunakan connectives (∧,¬,∨,⇒,⇔) dan menggunakan quantifiers (∀, ∃). Tidak ada simbol [] dan {{}} dalam FOL. TIDAK ADA SPASI PADA KONSTANTA --> benar: uu_tni | salah: uu tni. Salah juga: tantangan_digital/geopolitik_moder!!!. Pastikan tidak ada kelebihan maupun kekurangan tanda kurung, spasi, atau simbol lainnya. Tidak ada tanda sama dengan (=) dalam FOL. Pastikan gunakan simbol ∀ untuk mengungkap fakta, contohnya: semua lapang itu di luar → ∀x (lapang(x) → di_luar(x)). Jangan sampai antara premis FOL dan kesimpulan FOL tidak memiliki hubungan logis.",
    "examples": [
      {{
        "input_queries": {{
          "kalimat": "I met a tall man who loved to eat cheese, now I believe all tall people like cheese."
        }},
        "output": {{
          "kalimat": "I met a tall man who loved to eat cheese, now I believe all tall people like cheese.",
          "premis": "A tall man loves cheese.",
          "kesimpulan": "All tall people like cheese.",
          "terms_premis": [
            {{ "term": "x", "jenis": "variabel", "keterangan": "Representasi orang yang tidak spesifik menggantikan man" }},
            {{ "term": "cheese", "jenis": "konstanta", "keterangan": "Representasi objek spesifik yaitu makanan yang disukai oleh orang tinggi" }}
          ],
          "terms_kesimpulan": [
            {{ "term": "x", "jenis": "variabel", "keterangan": "Representasi orang yang tidak spesifik menggantikan people" }},
            {{ "term": "cheese", "jenis": "konstanta", "keterangan": "Representasi objek spesifik yaitu makanan yang disukai oleh orang tinggi" }}
          ],
          "predikat": [
            "Man(x)", "Tall(x)", "Loves(x, cheese)", "Eats(x, cheese)", "Person(x)", "Likes(x, cheese)"
          ],
          "fol": "(∃x (Man(x) ∧ Tall(x) ∧ Loves(x, cheese))) → (∀x (Tall(x) ∧ Person(x) → Likes(x, cheese)))"
        }}
      }}
    ],
    "input_queries": [
      {{
        "kalimat": "{kalimat}"
      }}
    ]
  }}
}}
"""
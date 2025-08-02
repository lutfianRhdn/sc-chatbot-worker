prompt_klasifikasi_template = """
{{
  "instructions": {{
    "task": "Identifikasi jenis logical fallacy hanya berdasarkan hubungan logis antara 'Premis' dan 'Kesimpulan', tanpa mempertimbangkan konteks luar atau kebenaran faktual dari 'Kalimat Argumen'.",
    "persona": "Anda adalah pakar logika dan analisis argumen, terlatih dalam mendeteksi kekeliruan berpikir (logical fallacies) dalam argumen alami.",
    "method": "1. Analisis apakah kesimpulan melebihi, tidak mengikuti, atau salah menyimpulkan dari premis.\\n2. Gunakan daftar fallacy dan interpretasi untuk mengevaluasi validitas logis.\\n3. Cocokkan dengan definisi dan karakteristik dari daftar fallacy umum.\\n4. 'fallacy_type' harus cocok dengan entri pada 'Daftar Fallacy' (case-sensitive). Jika tidak ada yang cocok, gunakan 'None'.",
    "output_format": Format JSON dengan field 'fallacy_type', 'fallacy_location', "kutipan", "feedback", dengan hasilnya adalah '"fallacy_type": "...","kutipan": "...","fallacy_location": "[]","feedback": "..."}'.,
    "handling_unknown": "Jika tidak ditemukan fallacy, isi 'fallacy_type' dengan 'None' dan kosongkan bagian lainnya."
  }},
  "context": {{
    "relevant_information": {{
      "premis": {premis},
      "kesimpulan": {kesimpulan},
      "daftar_fallacy": {fallacy_data},
      "interpretasi": {interpretasi}
    }},
    "input_query": {{
      "kalimat": "{kalimat}"
    }}
  }}
}}
"""
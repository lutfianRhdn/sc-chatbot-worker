prompt_progression_template = """{{
  "instructions": {{
    "persona": "Anda adalah seorang analis linguistik sistemik-fungsional dengan keahlian dalam teori Halliday.",
    "task": "Lakukan analisis thematic progression terhadap kalimat berikut. Jika ada masalah dalam alur tema, tunjukkan secara spesifik klausa mana yang bermasalah, kutipan kalimatnya, dan berikan saran perbaikannya.",
    "method": [
      "1. Analisis Klausa: Bagi teks menjadi klausa dan identifikasi theme (titik awal informasi) dan rheme (informasi baru) tiap klausa.",
      "2. Identifikasi Pola Thematic Progression: Tentukan apakah tiap klausa mengikuti pola berikut:",
      "- Constant Theme: Tema tetap sama di beberapa klausa.",
      "- Simple Linear Progression: Rheme sebelumnya jadi theme selanjutnya.",
      "- Derived Theme: Tema berbeda berasal dari satu tema induk.",
      "- Split Rheme Progression: Rheme bercabang ke beberapa theme selanjutnya.",
      "3. Evaluasi Koherensi dan Kohesi: Apakah antar klausa saling berhubungan secara topikal dan referensial.",
      "4. Identifikasi Masalah: Tandai klausa yang memiliki masalah perkembangan tema, termasuk abrupt/ruptured theme, pengulangan monoton, atau kurang transisi.",
      "5. Berikan Saran: Jika ada masalah, sebutkan kutipan klausa bermasalah, jenis masalahnya, dan saran spesifik perbaikannya."
    ],
    "handling_unknown": "Kosongkan jika tidak ada masalah ditemukan."
  }},
  "output_format": {{
    "kalimat": "<kalimat>",
    "theme_rheme_per_klausa": {{
      "klausa_1": {{
        "kalimat": "<isi klausa>",
        "theme": "<theme>",
        "rheme": "<rheme>"
      }},
      "...": {{}}
    }},
    "pola_thematic_progression": "<pola yang dominan atau campuran>",
    "koherensi": "<evaluasi koherensi>",
    "kohesi": "<evaluasi kohesi>",
    "masalah_thematic_progression": [
      {{
        "klausa": "<nomor klausa>",
        "kutipan": "<kutipan klausa yang bermasalah>",
        "jenis_masalah": "<jenis masalah thematic>",
        "feedback_progression": "<saran perbaikan untuk klausa tersebut>"
      }}
    ]
  }},
  "context": {{
    "relevant_information": "Masalah dalam thematic progression biasanya mencakup tema yang berganti tiba-tiba, tidak ada transisi, repetisi membosankan, atau struktur klausa ambigu.",
    "examples": [
      {{
        "kalimat": "Human history teems with stories of momentous blunders in a wide range of disciplines. Some of these consequential errors go all the way back to the Scriptures, or the Greek mythology.",
        "theme_rheme_per_klausa": {{
          "klausa_1": {{
            "kalimat": "Human history teems with stories of momentous blunders in a wide range of disciplines.",
            "theme": "Human history",
            "rheme": "teems with stories of momentous blunders in a wide range of disciplines."
          }},
          "klausa_2": {{
            "kalimat": "Some of these consequential errors go all the way back to the Scriptures, or the Greek mythology.",
            "theme": "Some of these consequential errors",
            "rheme": "go all the way back to the Scriptures, or the Greek mythology."
          }}
        }},
        "pola_thematic_progression": "Simple Linear Progression",
        "koherensi": "Alur hubungan antarklausa cukup jelas karena setiap theme pada klausa berikutnya tetap berkaitan erat dengan topik utama (blunders dalam sejarah).",
        "kohesi": "Penggunaan kata ganti seperti 'these errors' mengacu ke kesalahan pada kalimat sebelumnya, menjaga hubungan antar kalimat.",
        "masalah_thematic_progression": [],
        "feedback_progression": ""
      }},
      {{
        "kalimat": "The purpose of this book is to present in detail some of the surprising blunders of a few genuinely towering scientists. My goal is also to attempt to analyze the possible causes for these blunders.",
        "theme_rheme_per_klausa": {{
          "klausa_1": {{
            "kalimat": "The purpose of this book is to present in detail some of the surprising blunders of a few genuinely towering scientists.",
            "theme": "The purpose of this book",
            "rheme": "is to present in detail some of the surprising blunders of a few genuinely towering scientists."
          }},
          "klausa_2": {{
            "kalimat": "My goal is also to attempt to analyze the possible causes for these blunders.",
            "theme": "My goal",
            "rheme": "is also to attempt to analyze the possible causes for these blunders."
          }}
        }},
        "pola_thematic_progression": "Brand-New Theme",
        "koherensi": "Koheren secara umum karena membahas topik yang sama (tujuan buku).",
        "kohesi": "Terdapat referensi kohesif seperti 'these blunders'.",
        "masalah_thematic_progression": [
          {{
            "klausa": "2",
            "kutipan": "My goal is also to attempt to analyze the possible causes for these blunders.",
            "jenis_masalah": "Brand-New Theme",
            "feedback_progression": "Sebaiknya gunakan referensi eksplisit ke theme sebelumnya, seperti 'This purpose also includes...' untuk menjaga kontinuitas."
          }}
        ]
      }}
    ]
  }},
  "input_query": [
    {{
      "kalimat": "{kalimat}"
    }}
  ]
}}"""
prompt_intent_template = """
{{
    "instructions": {{
      "task": "Sebagai model bahasa AI, tugas Anda adalah menetapkan maksud (intent) yang benar untuk setiap kalimat teks yang diberikan.",
      "method": [
        "- Pahami konteks dan tujuan dari setiap kalimat.",
        "- Jangan pernah menetapkan intent sebagai 'tidak diketahui'.",
        "- Jika intent tidak sesuai dengan yang sudah Anda kenali, buatlah intent baru yang singkat dan bermakna.",
        "- Ucapan dapat berupa pertanyaan, permintaan, atau pernyataan.",
        "- Tanggapan Anda harus ringkas, akurat, dan relevan secara kontekstual."
      ],
      "output_format": {{
        "intent": "<intent>"
      }}
    }},
    "context": {{
      "examples": [
        {{
          "kalimat": "tolong nyalakan alarm untuk jam 6 pagi",
          "intent": "atur_alarm"
        }},
        {{
          "kalimat": "apa saldo rekening saya sekarang",
          "intent": "cek_saldo"
        }},
        {{
          "kalimat": "saya ingin memesan makanan dari restoran padang",
          "intent": "pesan_makanan"
        }},
        {{
          "kalimat": "berapa biaya transfer ke bank lain",
          "intent": "biaya_transfer"
        }},
        {{
          "kalimat": "kirim pesan ke Andi bahwa saya akan telat",
          "intent": "kirim_pesan"
        }}
      ],
      "input_queries": {{
        "kalimat": {kalimat}
      }}
    }}
  }}
}}
"""
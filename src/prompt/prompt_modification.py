prompt_modification_template = """{{
    "instructions": {{
        "task": "Perbaiki *hanya* bagian yang mengandung logical fallacy dalam kalimat, sehingga dihasilkan satu kalimat yang bebas dari logical fallacy dan tetap mempertahankan intent asli.",
        "persona": "Anda adalah editor argumen logis dan linguistik yang teliti.",
        "method": [
            "1) Analisis data dari relevant_information",
            "2) Implementasi perbaikan spesifik berdasarkan fallacy_type dan feedback yang tersedia",
            "3) Modifikasi bagian kalimat sesuai dengan fallacy_location dan kutipannya berdasarkan dengan feedback perbaikan",
            "4) Integrasikan perbaikan thematic_progression untuk memastikan alur logis",
            "5) Validasi hasil modifikasi terhadap intent dan konsistensi argumen"
        ],
        "output_format": {{
            "modified_sentence": "<kalimat hasil modifikasi>"
        }},
        "handling_unknown": "Jika elemen di 'relevant_information' kosong atau tidak ditemukan, biarkan field JSON-nya kosong tanpa menambah data."
    }},
    "context": {{
        "relevant_information": {{
            "premis": {premis},
            "kesimpulan": {kesimpulan},
            "intent": {intent},
            "fallacy_type": {fallacy_type_data},
            "fallacy_location": {fallacy_location},
            "feedback": {feedback},
            "thematic_progression": {masalah_thematic_progression}
        }},
        "example": {{
            "kalimat": "Karena ada beberapa pasal bermasalah, bukankah seharusnya seluruh Undang-Undang TNI direvisi?",
            "modified_sentence": "Karena ada beberapa pasal yang bermasalah dalam UU TNI, bukankah akan lebih tepat jika hanya pasal-pasal tersebut yang direvisi, bukan keseluruhan undang-undang?"
        }},
        "input_query": {{
            "kalimat": {kalimat}
        }}
    }}
}}"""
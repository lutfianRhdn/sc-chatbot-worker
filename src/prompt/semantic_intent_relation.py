prompt_intent_relationship_template = """{{
  "instructions": {{
    "task": "Periksa apakah intent 2 di-entail oleh intent 1. Jika intent 2 mencakup/mengandung makna intent 1 (entailment), maka labeli dengan 'entailment'. Jika tidak, labeli 'no entailment' dan berikan saran perbaikan pada field feedback agar intent 2 lebih mirip/lebih tepat maknanya dengan intent 1.",
    "persona": "Seorang ahli linguistik dan NLP spesialis intent_relationship entailment.",
    "method": "Bandingkan makna dan cakupan dua intent secara kritis. Jika intent 2 merupakan konsekuensi logis atau cakupannya tidak mungkin salah jika intent 1 benar, labeli 'entailment'. Jika tidak, labeli 'no entailment' dan berikan feedback.",
    "output_format": "Format JSON dengan field: {{'relationship': 'entailment | no entailment', 'feedback_intent': '<saran perbaikan>'}}",
    "handling_unknown": "Jika makna tidak bisa dibandingkan, kosongkan fieldnya."
  }},
  "context": {{
    "relevant_information": {{
      "kalimat_1": {prompt_user},
      "kalimat_2": {prompt_modification}
    }},
    "example": [
      {{
        "kalimat_1": "Seseorang membeli mobil.",
        "kalimat_2": "Seseorang memiliki mobil.",
        "intent_kalimat_1": "membeli_mobil",
        "intent_kalimat_2": "memiliki_mobil",
        "relationship": "entailment",
        "feedback": ""
      }},
      {{
        "kalimat_1": "Seseorang membaca buku novel.",
        "kalimat_2": "Seseorang menulis buku novel.",
        "intent_kalimat_1": "membaca_buku_novel",
        "intent_kalimat_2": "menulis_buku_novel",
        "relationship": "no entailment",
        "feedback": "Ubah intent kalimat 2 agar memiliki makna yang sejalan, misalnya menjadi 'seseorang membaca buku novel' atau 'seseorang telah selesai membaca buku novel'."
      }}
    ],
    "input_query": {{
      "intent_1": {semantic_intent_prompt},
      "intent_2": {semantic_intent_modif}
    }}
  }}
}}"""
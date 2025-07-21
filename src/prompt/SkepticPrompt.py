from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import AzureChatOpenAI



# Prompt
skeptic_prompt = PromptTemplate.from_template(
    """
    [previous opinions]: {previous_opinion}
    [text]: {claim}
    [evidences]: {evidence}
    Anda adalah agen Skeptis dari ketiga agen. "Skeptis" berarti Anda harus mempertanyakan pendapat agen sebelumnya dengan meneliti data yang tersedia [text] dan [evidences] serta mengidentifikasi kemungkinan kesalahan atau faktor menyesatkan dalam pendapat agen sebelumnya.
Anda diberikan opini yang dihasilkan oleh agen sebelumnya. Lihat klaim [text] dan bukti [evidences] untuk menganalisis opini [previous opinions] dari agen sebelumnya. Periksa dengan cermat apakah bukti yang sesuai mendukung pernyataan yang diajukan oleh agen sebelumnya. Jika Anda yakin ada bagian dari opininya yang salah, tunjukkan dan jelaskan perspektif Anda.
Kemudian periksa secara kritis validitas klaim [text], dengan mempertimbangkan potensi bias atau inkonsistensi antara informasi [evidences] dan klaim [text].
JANGAN MENGULANGI pendapat agen sebelumnya, Anda harus mengembangkan perspektif Anda sendiri berdasarkan pendapat mereka.
Ambil pendapat agen sebelumnya sebagai referensi daripada menyalinnya secara langsung.
Pastikan Anda menyebutkan sumber dari bukti yang Anda gunakan untuk mendukung penilaian Anda.

Kategori Halusinasi Faktualitas & Sub-tipenya:
A. Factual Contradiction
Terjadi ketika keluaran model bertentangan secara langsung dengan fakta yang dapat diverifikasi dari dunia nyata.

a. Entity-error  
Kesalahan pada entitas yang disebut.  
Contoh:  
Klaim: "RUU TNI disahkan oleh Presiden."  
Fakta: RUU TNI disahkan oleh DPR pada 20 Maret 2025, bukan oleh Presiden.

b. Relation-error  
Kesalahan dalam hubungan antar entitas.  
Contoh:  
Klaim: "RUU TNI memberi wewenang kepada TNI untuk mengatur proses pemilu"  
Fakta: RUU TNI tidak memberikan kewenangan kepada TNI untuk mengatur pemilu. Penyelenggaraan pemilu merupakan wewenang KPU, bukan institusi militer.

B. Factual Fabrication  
Terjadi ketika model menghasilkan informasi yang tidak dapat diverifikasi atau tidak memiliki dasar fakta.

a. Unverifiability hallucination  
Klaim tidak bisa dibuktikan karena entitas atau peristiwanya tidak pernah ada.  
Contoh:  
Klaim: "RUU TNI mewajibkan setiap warga sipil mengikuti pelatihan militer wajib setiap tahun."  
Masalah: Tidak ada aturan dalam RUU TNI yang mewajibkan pelatihan militer tahunan bagi warga sipil; klaim ini tidak memiliki dasar hukum.
ubah 
b. Overclaim hallucination  
Klaim berlebihan yang menyiratkan validitas universal tanpa dasar kuat.  
Contoh:  
Klaim: "RUU TNI 2025 secara bulat didukung oleh seluruh rakyat Indonesia.""  
Masalah: Klaim ini terlalu umum dan tidak akurat karena terdapat banyak protes serta kritik dari berbagai kelompok masyarakat sipil terhadap isi RUU tersebut.

Tanggapan harus berupa kamus dengan dua kunci - `"opinion"` dan `"factuality"` yang menjelaskan apakah teks yang diberikan faktual atau tidak (Boolean - True atau False).
ANDA HANYA BOLEH MERESPONS DALAM FORMAT SEPERTI YANG DIJELASKAN DI BAWAH INI. JANGAN MENGEMBALIKAN APA PUN SELAIN ITU.
[response format]:
{{
"opinion": "Pertama, analisis pendapat agen sebelumnya, tunjukkan apa yang menurut Anda benar atau salah dalam pendapatnya dan jelaskan alasannya. Ingatlah bahwa Anda harus meragukan pendapat agen sebelumnya semaksimal mungkin. Kemudian, jelaskan pendapat Anda tentang faktualitas klaim [text] berdasarkan bukti [evidences], dengan menyebutkan secara eksplisit bukti mana yang mendukung atau menyangkal klaim. Sertakan rujukan ke sumber bukti (misalnya, URL tertentu dari [evidences]). JANGAN MENGULANGI PENDAPAT AGEN SEBELUMNYA [previous opinions].",
"factuality": True jika klaim tidak mengandung satu pun bentuk halusinasi faktual, False jika sebaliknya.
}}
"""
)


# Chain
# skeptic_chain = skeptic_prompt | llm | StrOutputParser()



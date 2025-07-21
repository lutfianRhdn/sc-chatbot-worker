from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import AzureChatOpenAI




# Prompt
leader_prompt = PromptTemplate.from_template(
    """

    [previous opinions]: {previous_opinion}
    [text]: {claim}
    [evidences]: {evidence}

Anda adalah agen Pemimpin dari ketiga agen. Dua agen lainnya adalah agen 'Skeptis' dan 'Kepercayaan'. Agen 'Skeptis' akan meragukan pendapat agen sebelumnya sesegera mungkin dan Agen 'Kepercayaan' akan mempercayai pendapat agen sebelumnya sesegera mungkin. 
Anda diberikan opini yang dihasilkan oleh dua agen sebelumnya. Gabungkan opini [previous opinions] yang diberikan oleh agen 'Skeptis' dan 'Kepercayaan' untuk mensintesis kesimpulan yang paling akurat dan dapat diandalkan mengenai kebenaran klaim ([text]) berdasarkan [evidences]. Anda perlu mempertimbangkan karakteristik kedua agen ini saat membentuk opini Anda sendiri. Nilai kekuatan dan kelemahan kedua belah pihak, dan manfaatkan informasi yang diberikan untuk menghasilkan penilaian konklusif.
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
"opinion": "Pertama, jelaskan pandangan Anda tentang pendapat dua agen sebelumnya. Kemudian, jelaskan pendapat Anda tentang kebenaran klaim [text] berdasarkan bukti-bukti [evidences]. Pendapat Anda harus didukung oleh bukti yang sesuai. JANGAN ULANGI PENDAPAT AGEN SEBELUMNYA [previous opinions]. Dengan merujuk pada pendapat agen “Trust” dan agen “Skeptic”, tentukan pendapat baru yang menurut Anda benar",
"factuality": True jika klaim tidak mengandung satu pun bentuk halusinasi faktual, False jika sebaliknya.
}}
"""
)






# Chain
# leader_chain = leader_prompt | llm | StrOutputParser()

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import AzureChatOpenAI




# Prompt
prompt = PromptTemplate.from_template(
    """Peran Anda: Seorang ahli yang membantu orang dalam menggali informasi dalam sebuah topik.

Ketentuan:
1. Jawaban hanya boleh memuat fakta eksplisit dalam *Context*—tanpa asumsi, opini, atau tambahan lain.
2. Hindari:
   • *Contradiction*: jangan ubah/­tambah data (nama, tanggal, relasi) yang tidak disebutkan.  
   • *Fabrication*: jangan menulis info tak diverifikasi atau klaim berlebihan.
3. Batas referensi:
    • Gunakan maksimal 10 sumber saja.
    • Dari daftar referensi yang tersedia di dalam Context, gunakan hanya yang benar-benar dikutip dalam isi jawaban.
    • Nomor referensi harus dimulai dari [1] dan terus berlanjut sesuai urutan pertama kali dikutip.
    • Jangan gunakan kutipan [n] jika [n–1] belum digunakan. Tidak boleh melompati urutan.
    • Jangan tampilkan referensi yang tidak digunakan.
    • Setiap fakta atau klaim yang berasal dari referensi harus segera diikuti oleh nomor referensinya ([1], [2], dst).
Daftar referensi harus persis mencerminkan nomor yang muncul dalam isi jawaban.
4. Format jawaban  
   • Buka dengan: “Berdasarkan informasi yang ada, …”  
   • Sitasi angka [1], [2], … (gunakan nomor sama untuk sumber yang sama; jangan lakukan sitasi jika tidak dipakai).  
   • Daftar referensi (URL) di akhir dan selalu dimulai dari nomor [1].  
   • Tutup dengan: “Terima kasih telah bertanya, apakah ada hal lain yang ingin Anda tanyakan?”

Pertanyaan: {question}  
Context: "{context}"  
Jawaban:

"""
)


# Post-processing
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


# Chain
# rag_chain = prompt | llm | StrOutputParser()

# Run
# generation = rag_chain.invoke({"context": docs, "question": question})
# print(generation)
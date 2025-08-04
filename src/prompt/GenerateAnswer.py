from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import AzureChatOpenAI




# Prompt
prompt = PromptTemplate.from_template(
    """Peran Anda: Seorang ahli politik yang membantu orang dalam menggali informasi dalam sebuah topik.

Ketentuan:
1. Jawaban hanya boleh memuat fakta eksplisit dalam *Context*—tanpa asumsi, pengetahuan umum, opini, atau tambahan lain.
2. Hindari:
   • *Contradiction*: jangan ubah/­tambah data (nama, tanggal, relasi) yang tidak disebutkan.  
   • *Fabrication*: jangan menulis info tak diverifikasi atau klaim berlebihan.
3. Batas referensi:
    • Anda hanya boleh menggunakan **maksimal 10 sumber**, meskipun ada lebih banyak sumber yang tersedia.
    • Jika ada lebih dari 10 sumber yang relevan, pilihlah hanya 10 sumber yang paling relevan dengan pertanyaan.
    • Dalam keadaan apa pun, jangan menggunakan atau mengutip lebih dari 10 referensi.  
    • Setiap referensi harus dikutip menggunakan format [1], [2], dll., **sesuai urutan pertama kali dikutip**.  
    • Di akhir jawaban, berikan daftar sumber yang tepat yang telah dikutip—tidak lebih, tidak kurang.  
    • Jangan mencantumkan referensi yang tidak digunakan. Jangan mengulang referensi dalam daftar lebih dari sekali.
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
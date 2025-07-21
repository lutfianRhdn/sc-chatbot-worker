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
3. Format jawaban  
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
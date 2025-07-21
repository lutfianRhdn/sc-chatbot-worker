from langchain.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_openai import AzureChatOpenAI



# Data model
class GradeDocuments(BaseModel):
    """Klasifikasi relevansi dokumen."""

    final_classification: str = Field(
        description="Klasifikasi akhir dokumen: 'Benar', 'Salah', atau 'Ambigu'."
    )

# LLM with function call
# structured_llm_grader = llm.with_structured_output(GradeDocuments)

# System Prompt
system = """Anda adalah evaluator penelusuran yang bertugas menilai apakah suatu dokumen menyediakan informasi yang relevan untuk menjawab pertanyaan yang diberikan. \n
Berdasarkan penilaian Anda, klasifikasikan dokumen ke dalam salah satu kategori berikut:\n
- Benar:  Dokumen mengandung informasi yang akurat dan relevan, serta dapat dipetakan secara logis ke pertanyaan.\n
- Salah: Dokumen mengandung informasi yang bertentangan dengan fakta atau tidak relevan, dan tidak ada bagian dari dokumen yang mendukung jawaban pertanyaan.\n
- Ambigu: Dokumen mengandung informasi yang tidak jelas, hanya menjawab sebagian pertanyaan, atau dapat diinterpretasikan dengan lebih dari satu cara tanpa kejelasan.\n
    Jawab pertanyaan evaluasi berikut:\n
1. Apakah informasi yang diberikan dalam dokumen secara langsung menjawab inti dari pertanyaan yang diajukan? [Ya/Tidak]\n
2. Apakah ada bagian dari dokumen yang membingungkan atau dapat ditafsirkan dengan lebih dari satu cara? [Ya/Tidak]\n
3. Apakah dokumen menyertakan semua informasi yang relevan untuk menjawab pertanyaan dengan lengkap? [Ya/Tidak]\n
4. Apakah dokumen mengandung informasi yang bertentangan atau tidak konsisten dengan fakta atau pengetahuan umum yang berlaku? [Ya/Tidak]\n
Keputusan Akhir:\n
- Benar > Jika jawaban untuk (1) dan (3) adalah 'Ya'.\n
- Salah > Jika jawaban (1) adalah 'Tidak' ATAU jawaban (4) adalah 'Ya'.\n
- Ambigu > Jika jawaban (2) adalah 'Ya' sementara (1) atau (3) tidak jelas.\n
Pertanyaan: {question}\n
Dokumen yang Diambil: {document}\n"""

# Chat prompt template
grade_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "Evaluasi dokumen ini untuk relevansi: \n\n Dokumen: {document} \n\n Pertanyaan pengguna: {question}"),
    ]
)

# Create a retrieval grader pipeline
# retrieval_grader = grade_prompt | structured_llm_grader


# # Render final prompt
# formatted_prompt = grade_prompt.format(question=question, document=doc_txt)
# print("==== FINAL PROMPT YANG DIKIRIMKAN KE LLM ====")
# print(formatted_prompt)
# print("=============================================")

# Invoke the grading system
# print(retrieval_grader.invoke({"question": question, "document": doc_txt}))

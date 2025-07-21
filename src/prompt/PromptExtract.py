from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import AzureChatOpenAI




# Prompt
prompt_extrac = PromptTemplate.from_template(
    """Anda diberikan sebuah potongan teks, harap hapus kalimat-kalimat yang menurut Anda sepenuhnya merupakan opini pribadi dan tidak mengandung informasi faktual apa pun. Output Anda harus berupa kalimat setelah dimodifikasi dari konten asli. Jika menurut Anda seluruh kalimat adalah opini pribadi, harap keluarkan *None*. Berikut dua contohnya:
[text]: Senang sekali, beri tahu saya jika Anda butuh rekomendasi lainnya.
[response]: None
[text]: RUU TNI disahkan dalam rapat paripurna DPR pada 20 Maret 2025. Sudahkah kau membacanya?
[response]: RUU TNI disahkan dalam rapat paripurna DPR pada 20 Maret 2025.
Sekarang selesaikan yang berikut ini
[text]: {input}
[response]:
"""
)





# Chain
# extract_chain = prompt_extrac | llm | StrOutputParser()

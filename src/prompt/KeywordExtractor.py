from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import AzureChatOpenAI





system = """Anda adalah pengekstrak kata kunci. Tugas Anda adalah mengekstrak paling banyak tiga kata kunci yang dipisahkan oleh koma dari pertanyaan berikut. Fokuslah pada tujuan utama (dari pertanyaan). Kata kunci ini akan digunakan sebagai kueri untuk pencarian web."""
re_write_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        (
            "human",
            """Ekstrak paling banyak tiga kata kunci yang dipisahkan dengan koma dari pertanyaan berikut sebagai kueri untuk pencarian web, termasuk niat utama dalam pertanyaan.
pertanyaan: Apa isi utama RUU TNI?
kueri: isi, RUU TNI
pertanyaan: Siapa yang menyusun RUU TNI?
kueri: penyusun, RUU TNI
pertanyaan: Bagaimana dampak RUU TNI terhadap militer Indonesia?
kueri: dampak, RUU TNI, militer Indonesia
pertanyaan: Kapan RUU TNI disahkan?
kueri: waktu, pengesahan, RUU TNI
pertanyaan: {question}
kueri:""",
        ),
    ]
)

# keyword_extractor = re_write_prompt | llm | StrOutputParser()
# keyword_extractor.invoke({"question": question})


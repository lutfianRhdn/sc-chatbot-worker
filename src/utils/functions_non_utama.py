from openai import AzureOpenAI
import pandas as pd 
import re
import subprocess
from utils.cvc import CVCGenerator
import json
from groq import Groq
import re
from openai import OpenAI
import os


def remove_json_text(text):
    # Menghapus ```json di awal dan ``` di akhir
    modified_string = text.replace("```json\n{", "").replace("```", "").replace("\n}", "").strip()

    return modified_string

def llm(prompt):
    client = AzureOpenAI(
        azure_endpoint = "endpoint", 
        api_key="key",  
        api_version="api-version"
        )

    response = client.chat.completions.create(
        model="gpt-4.1", # model = "deployment_name".
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    respons_text = remove_json_text(response.choices[0].message.content)
    return respons_text

def llm_qwen(prompt):
    client = OpenAI(
        base_url="base_url",
        api_key="key",
    )

    completion = client.chat.completions.create(
    # model="deepseek/deepseek-chat-v3-0324:free",
    model="qwen/qwen3-235b-a22b-07-25:free",
    messages=[
        {
        "role": "user",
        "content": prompt
        }
    ]
    )
    def extract_and_format_fol(text):
        match = re.search(r'"fol"\s*:\s*"([^"]+)"', text)
        
        if match:
            fol_string = match.group(1)  # Ambil grup 1 (isi di dalam kutip)
            # Format ulang menjadi {"fol": " [isi] "}
            formatted = f'{{"fol": "{fol_string}"}}'
            return formatted
        else:
            return "String FOL tidak ditemukan dalam teks."

    # Eksekusi
    # print(f"Ini hasilnya deepsek: {completion.choices[0].message.content}")
    result = extract_and_format_fol(completion.choices[0].message.content)

    respons_text = remove_json_text(result)
    return respons_text

def get_dataset():
    dataset = pd.read_excel("dataset.xlsx")
    return dataset 


def get_counter_example(fol_keseluruhan):

    # Mengganti simbol ∃ dengan 'exists', ∀ dengan 'forall', ∧ dengan 'and', → dengan 'implies', dan ∨ dengan 'or'
    fol_standardized = re.sub(r"∃", "exists ", fol_keseluruhan)
    fol_standardized = re.sub(r"∀", "forall ", fol_standardized)
    fol_standardized = re.sub(r"∧", "and", fol_standardized)
    fol_standardized = re.sub(r"&", "and", fol_standardized)
    fol_standardized = re.sub(r"→", "->", fol_standardized)
    fol_standardized = re.sub(r"⇒", "->", fol_standardized)
    fol_standardized = re.sub(r"∨", "or", fol_standardized)
    fol_standardized = re.sub(r"¬", "not", fol_standardized)

    try:
        # Proses mengganti kata kunci sesuai dengan format SMT-LIB
        script = CVCGenerator(fol_standardized).generateCVCScript()
        # Menyimpan skrip SMT-LIB ke dalam file
        with open("logical_form.smt2", "w") as f:
            f.write(script)

        # Menjalankan CVC5 solver dan menangkap output
        base_path = os.path.dirname(os.path.abspath(__file__))
        cvc5_path = os.path.join(base_path,'../cvc5/unix/bin/cvc5')
        proc = subprocess.run([cvc5_path, "--lang", "smt2", "logical_form.smt2"], capture_output=True, text=True, check=True)
        proc_result = proc.stdout

        # Menyimpan hasil output solver ke file
        with open("logical_form_out.txt", "w") as f:
            f.write(proc_result)
        
        # print(f"Output CVC5:\n{proc_result}")
        return proc_result
    
    except Exception as e:
        return f"Terjadi kesalahan: {e}"
    
def load_prompt_template(filename):
    """Load prompt template from JSON file"""
    # print(f"Loading prompt template from {filename}")
    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
        json_file_path = os.path.join(base_path, '../prompt/', filename)
        
        with open(json_file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"template": "", "variables": []}
        
def fix_json_if_incomplete(json_str):
    # print(f"Fixing JSON if incomplete: {json_str}")
    try:
        # Coba parsing dulu
        data = json.loads(json_str)
        return data  # Jika berhasil, tidak perlu perbaiki
    except json.JSONDecodeError as e:
        # Jika error karena tidak lengkap (biasanya karakter terakhir tidak cukup)
        if "Expecting value" in str(e) or "Expecting ',' delimiter" in str(e):
            # print("JSON tidak lengkap. Menambahkan '}' di akhir...")
            json_str += '}'
            print(f"Ini JSON String Sekarang: {json_str}")
            return json.loads(str(json_str))
        else:
            raise  # Jika error lainnya, lempar kembali
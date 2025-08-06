
import json
import os

def load_prompt_template(filename):
    """Load prompt template from JSON file"""
    # print(f"Loading prompt template from {filename}")
    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
        print(f"base path:{base_path}")
        json_file_path = os.path.join(base_path, '../prompt/', filename)
        print(f"load prompt : {json_file_path}")
        with open(json_file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"template": "", "variables": []}
        

def fix_json_if_incomplete(json_str):
  print(f"Fixing JSON if incomplete: {json_str}")
  try:
      # Coba parsing dulu
      data = json.loads(json_str)
      return data  # Jika berhasil, tidak perlu perbaiki
  except json.JSONDecodeError as e:
      # Jika error karena tidak lengkap (biasanya karakter terakhir tidak cukup)
      if "Expecting value" in str(e) or "Expecting ',' delimiter" in str(e):
          print("JSON tidak lengkap. Menambahkan '}' di akhir...")
          json_str += '}'
          return json.loads(json_str)
      else:
          raise  # Jika error lainnya, lempar kembali
        


def remove_json_text(text):
    # Menghapus ```json di awal dan ``` di akhir
    modified_string = text.replace("```json\n{", "").replace("```", "").replace("\n}", "").strip()

    return modified_string

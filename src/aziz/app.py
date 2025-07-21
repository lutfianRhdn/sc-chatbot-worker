# FLASK 
from flask import Flask, request, jsonify
from flask_cors import CORS
from function_utama import transformasi_respons_chatbot_ke_fol, pembuatan_counter_example, klasifikasi_logical_fallacies
from functions_non_utama import llm, load_prompt_template, fix_json_if_incomplete

app = Flask(__name__)
CORS(app)   

def modify_respons(respons):
    chain_1, chain_2, chain_3, chain_4, fol_keseluruhan = transformasi_respons_chatbot_ke_fol(respons)
    interpretasi_counter_example = pembuatan_counter_example(respons, fol_keseluruhan)
    logical_fallacy = klasifikasi_logical_fallacies(interpretasi_counter_example)
    return chain_1, chain_2, chain_3, chain_4, fol_keseluruhan, interpretasi_counter_example, logical_fallacy

@app.route('/lfu', methods=['POST'])
def logical_fallacy_understanding():
    try:
        # Mendapatkan URL gambar dari request
        data = request.json
        respons_chatbot = data.get('respons_chatbot')
        chain_1, chain_2, chain_3, chain_4, fol_keseluruhan, interpretasi_counter_example, logical_fallacy = modify_respons(respons_chatbot)
        return jsonify({
            'status': 'success',
            'message': 'Transformasi berhasil',
            'premis_kesimpulan': fix_json_if_incomplete(chain_1),
            'terms': fix_json_if_incomplete(chain_2),
            'atomic_formula': fix_json_if_incomplete(chain_3),
            'fol_keseluruhan': fol_keseluruhan,
            'interpretasi_counter_example': fix_json_if_incomplete(interpretasi_counter_example),
            'logical_fallacy': fix_json_if_incomplete(logical_fallacy)
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

if __name__ == "__main__":
    app.run(debug=True)
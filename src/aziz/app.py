# FLASK 
from flask import Flask, request, jsonify
from flask_cors import CORS
from function_utama import function_transformasi_respons_chatbot_ke_fol, function_pembuatan_counter_example, function_klasifikasi_logical_fallacies, function_perbaikan_respons_chatbot
from functions_non_utama import llm, load_prompt_template, fix_json_if_incomplete

app = Flask(__name__)
CORS(app)   

def modify_respons(respons):
    transformasi_respons_chatbot_ke_fol = function_transformasi_respons_chatbot_ke_fol(respons)
    pembuatan_counter_example = function_pembuatan_counter_example(respons, transformasi_respons_chatbot_ke_fol['chain_4']['fol_keseluruhan'])
    klasifikasi_logical_fallacy = function_klasifikasi_logical_fallacies(respons, pembuatan_counter_example['interpretasi_counter_example'])
    modifikasi_respons_chatbot = function_perbaikan_respons_chatbot(respons, pembuatan_counter_example['interpretasi_counter_example'], klasifikasi_logical_fallacy)
    return transformasi_respons_chatbot_ke_fol, pembuatan_counter_example, klasifikasi_logical_fallacy, modifikasi_respons_chatbot

@app.route('/lfu', methods=['POST'])
def logical_fallacy_understanding():
    try:
        # Mendapatkan data respons chatbot dari request
        data = request.json
        respons_chatbot = data.get('respons_chatbot')

        # Proses logic fallacy understanding
        transformasi_respons_chatbot_ke_fol, pembuatan_counter_example, klasifikasi_logical_fallacy, modifikasi_respons_chatbot = modify_respons(respons_chatbot)
        # END

        return jsonify({
            'chain_1': transformasi_respons_chatbot_ke_fol['chain_1'],
            'chain_2': transformasi_respons_chatbot_ke_fol['chain_2'],
            'chain_3': transformasi_respons_chatbot_ke_fol['chain_3']['atomic_formula'],
            'chain_4': transformasi_respons_chatbot_ke_fol['chain_4']['fol_keseluruhan'],
            'pembuatan_counter_example': pembuatan_counter_example,
            'klasifikasi_logical_fallacy': klasifikasi_logical_fallacy,
            'modifikasi_respons_chatbot': modifikasi_respons_chatbot
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

if __name__ == "__main__":
    app.run(debug=True)
# FLASK 
from flask import Flask, request, jsonify
from flask_cors import CORS
from function_utama import function_transformasi_respons_chatbot_ke_fol, function_pembuatan_counter_example, function_klasifikasi_logical_fallacies, function_perbaikan_respons_chatbot, function_analisis_thematic_progression
from functions_non_utama import llm, load_prompt_template, fix_json_if_incomplete

app = Flask(__name__)
CORS(app)   

def modify_respons(respons):
    transformasi_respons_chatbot_ke_fol = function_transformasi_respons_chatbot_ke_fol(respons)
    
    pembuatan_counter_example = function_pembuatan_counter_example(respons, transformasi_respons_chatbot_ke_fol['chain_1']['premis'], transformasi_respons_chatbot_ke_fol['chain_1']['kesimpulan'], transformasi_respons_chatbot_ke_fol['chain_2']['terms_premis'], transformasi_respons_chatbot_ke_fol['chain_2']['terms_kesimpulan'], transformasi_respons_chatbot_ke_fol['chain_3']['atomic_formula'], transformasi_respons_chatbot_ke_fol['chain_4']['fol'])
    
    klasifikasi_logical_fallacy = function_klasifikasi_logical_fallacies(respons, pembuatan_counter_example['interpretasi_counter_example'])
    
    identifikasi_thematic_progression = function_analisis_thematic_progression(transformasi_respons_chatbot_ke_fol['chain_1']['premis'], transformasi_respons_chatbot_ke_fol['chain_1']['kesimpulan'])
    modifikasi_respons_chatbot = function_perbaikan_respons_chatbot(respons, pembuatan_counter_example['interpretasi_counter_example'], klasifikasi_logical_fallacy, identifikasi_thematic_progression['identifikasi_masalah_thematic_progression'])
    print("❇️ Ini hasil Transformasi Respons Chatbot ke FOL")
    print(transformasi_respons_chatbot_ke_fol)
    print()
    print("🗡️ Ini hasil Pembuatan Counterexample")
    print(pembuatan_counter_example)
    print()
    print("🧠 Ini hasil Klasifikasi Logical Fallacy")
    print(klasifikasi_logical_fallacy)
    print()
    print("🧮 Ini Hasil Identifikasi TP")
    print(identifikasi_thematic_progression)
    return transformasi_respons_chatbot_ke_fol, pembuatan_counter_example, klasifikasi_logical_fallacy, identifikasi_thematic_progression, modifikasi_respons_chatbot


@app.route('/lfu', methods=['POST'])
def logical_fallacy_understanding():
    try:
        # Mendapatkan data respons chatbot dari request
        data = request.json
        respons_chatbot = data.get('respons_chatbot')

        # Proses logic fallacy understanding
        transformasi_respons_chatbot_ke_fol, pembuatan_counter_example, klasifikasi_logical_fallacy, identifikasi_thematic_progression, modifikasi_respons_chatbot = modify_respons(respons_chatbot)
        # END

        import os

        # Menghapus file tunggal
        try:
            os.remove(r"D:\Kuliah\SKRIPSI\Sidang\socialabs-chatbot\logical_form.smt2")
            os.remove(r"D:\Kuliah\SKRIPSI\Sidang\socialabs-chatbot\logical_form.out")
            print("File berhasil dihapus")
        except FileNotFoundError:
            print("File tidak ditemukan")
        except PermissionError:
            print("Tidak memiliki izin untuk menghapus file")
        except Exception as e:
            print(f"Error: {e}")

        return jsonify({
            'chain_1': transformasi_respons_chatbot_ke_fol['chain_1'],
            'chain_2': transformasi_respons_chatbot_ke_fol['chain_2'],
            'chain_3': transformasi_respons_chatbot_ke_fol['chain_3']['atomic_formula'],
            'chain_4': transformasi_respons_chatbot_ke_fol['chain_4']['fol'],
            'pembuatan_counter_example': pembuatan_counter_example,
            'klasifikasi_logical_fallacy': klasifikasi_logical_fallacy,
            'Problems TP': identifikasi_thematic_progression['identifikasi_masalah_thematic_progression'],
            'modifikasi_respons_chatbot': modifikasi_respons_chatbot
        })
        

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

if __name__ == "__main__":
    app.run(debug=True)
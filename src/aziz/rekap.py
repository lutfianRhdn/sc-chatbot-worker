from function_utama import function_transformasi_respons_chatbot_ke_fol, function_pembuatan_counter_example, function_klasifikasi_logical_fallacies, function_perbaikan_respons_chatbot, function_analisis_thematic_progression
from functions_non_utama import llm, load_prompt_template, fix_json_if_incomplete

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

import pandas as pd

data = pd.read_excel(r"D:\Kuliah\SKRIPSI\Sidang\socialabs-chatbot\src\aziz\log_percakapan.xlsx")
jawabans = data['jawaban']

fols = []
smts = []
klasifikasi_logical_fallacies = []
modifikasis = []
jawabans_saat_ini = []
i = 1
for jawaban in jawabans[8:9]:
    # Proses logic fallacy understanding
    transformasi_respons_chatbot_ke_fol, pembuatan_counter_example, klasifikasi_logical_fallacy, identifikasi_thematic_progression, modifikasi_respons_chatbot = modify_respons(jawaban)
    # END

    fols.append(transformasi_respons_chatbot_ke_fol['chain_4']['fol'])
    smts.append(pembuatan_counter_example['hasil_smt_solver'][:7])
    klasifikasi_logical_fallacies.append(klasifikasi_logical_fallacy['jenis'])
    modifikasis.append(modifikasi_respons_chatbot['kalimat_keseluruhan'])
    jawabans_saat_ini.append(jawaban)
    
    print(f"-------- {i} ----------")
    i += 1

    # hasil = pd.DataFrame({'jawababn': jawabans_saat_ini, 'fol': fols, 'smt': smts, 'klasifikasi_logical_fallacy': klasifikasi_logical_fallacies, 'perbaikan': modifikasis})
    # hasil.to_excel("Rekap Perbaikan Aziz.xlsx", index=False)
from functions_non_utama import load_prompt_template, llm, llm_qwen, fix_json_if_incomplete
from get_counter_example import get_counter_example
import json

def function_transformasi_respons_chatbot_ke_fol(respons):
    chains = ["premis_kesimpulan.json", "terms.json", "atomic_formula.json", "fol.json"]

    for chain in chains:
        if chain == "premis_kesimpulan.json":
            prompt = load_prompt_template(chain)
            prompt['context']['input_queries']['respons_chatbot'] = respons
            prompt = json.dumps(prompt, indent=4)
            chain_1 = llm(prompt)
            print(f"❇️ Hasil Chain 1: {chain_1}")
            print()
        elif chain == "terms.json":
            prompt = load_prompt_template(chain)
            data = fix_json_if_incomplete(chain_1)
            premis = data['premis']
            kesimpulan = data['kesimpulan']
            prompt['context']['input_queries']['premis'] = premis
            prompt['context']['input_queries']['kesimpulan'] = kesimpulan
            prompt = json.dumps(prompt, indent=4)
            chain_2 = llm(prompt)
            print(f"❇️ Hasil Chain 2: {chain_2}")
            print()
        elif chain == "atomic_formula.json":
            prompt = load_prompt_template(chain)
            data = fix_json_if_incomplete(chain_2)
            term_premis = data['terms_premis']
            term_kesimpulan = data['terms_kesimpulan']
            prompt['context']['input_queries']['premis'] = premis
            prompt['context']['input_queries']['kesimpulan'] = kesimpulan
            prompt['context']['input_queries']['term_premis'] = term_premis
            prompt['context']['input_queries']['term_kesimpulan'] = term_kesimpulan
            prompt = json.dumps(prompt, indent=4)
            chain_3 = llm(prompt)
            print(f"❇️ Hasil Chain 3: {chain_3}")
            print()
        elif chain == "fol.json":
            prompt = load_prompt_template(chain)
            data_chain_1 = fix_json_if_incomplete(chain_1)
            data_chain_2 = fix_json_if_incomplete(chain_2)
            data_chain_3 = fix_json_if_incomplete(chain_3)
            premis = data_chain_1['premis']
            kesimpulan = data_chain_1['kesimpulan']
            term_premis = data_chain_2['terms_premis']
            term_kesimpulan = data_chain_2['terms_kesimpulan']
            atomic_formula = data_chain_3['atomic_formula']
            prompt['context']['input_queries']['respons_chatbot'] = respons
            prompt['context']['input_queries']['premis'] = premis
            prompt['context']['input_queries']['kesimpulan'] = kesimpulan
            prompt['context']['input_queries']['term_premis'] = term_premis
            prompt['context']['input_queries']['term_kesimpulan'] = term_kesimpulan
            prompt['context']['input_queries']['atomic_formula'] = atomic_formula
            prompt = json.dumps(prompt, indent=4)
            chain_4 = llm(prompt)
            fol = fix_json_if_incomplete(chain_4)
            fol = fol['fol']
            print(f"❇️ Hasil Chain 4: {chain_4}")
            print()

    transformasi_respons_chatbot_ke_fol = {
        'chain_1': {
            'premis': premis,
            'kesimpulan': kesimpulan
        },
        'chain_2': {
            'terms_premis': term_premis,
            'terms_kesimpulan': term_kesimpulan
        },
        'chain_3': {
            'atomic_formula': atomic_formula
        },
        'chain_4': {
            'fol': fol
        }
    }
    return transformasi_respons_chatbot_ke_fol

def function_pembuatan_counter_example(respons, premis, kesimpulan, terms_premis, terms_kesimpulan, atomic_formula, fol):
    try:
        hasil_smt_solver = get_counter_example(fol)
    except Exception as e:
        hasil_smt_solver = "Tidak ada."
    prompt = load_prompt_template("interpretasi_counter_example.json")
    prompt['context']['relevant_information']['respons_chatbot'] = respons
    prompt['context']['relevant_information']['premis'] = premis
    prompt['context']['relevant_information']['kesimpulan'] = kesimpulan
    prompt['context']['relevant_information']['terms_premis'] = terms_premis
    prompt['context']['relevant_information']['terms_kesimpulan'] = terms_kesimpulan
    prompt['context']['relevant_information']['atomic_formula'] = atomic_formula
    prompt['context']['relevant_information']['fol'] = fol
    prompt['context']['input_queries']['hasil_smt_solver'] = hasil_smt_solver
    prompt = json.dumps(prompt, indent=4)
    interpretasi_counter_example = llm(prompt)
    print(f"❇️ Hasil Interpretasi Counter Example: {interpretasi_counter_example}")
    print()

    try:
        # Buka dan baca file smt2
        with open('logical_form.smt2', 'r') as file:
            smt2_content = file.read()
    except Exception as e:
        smt2_content = "Tidak ada."

    pembuatan_counter_example = {
        'konversi_fol_ke_smt': smt2_content,
        'hasil_smt_solver': hasil_smt_solver,
        'interpretasi_counter_example': fix_json_if_incomplete(interpretasi_counter_example)['interpretasi_counter_example']
    }   
    return pembuatan_counter_example

def function_analisis_thematic_progression(premis, kesimpulan):
    prompt = load_prompt_template("theme_rheme.json")
    kalimat = ' '.join(premis) + ' ' + kesimpulan
    prompt['context']['input_queries']['kalimat'] = kalimat 
    prompt = json.dumps(prompt, indent=4)
    pola_tp = llm(prompt)
    print(f"❇️ Hasil Pola TP: {pola_tp}")
    print()
    pola_tp = fix_json_if_incomplete(pola_tp)

    prompt = load_prompt_template("problems_thematic_progression.json")
    prompt['context']['input_queries']['kalimat'] = kalimat
    prompt['context']['input_queries']['identifikasi_theme_rheme'] = pola_tp['identifikasi_theme_rheme']
    prompt['context']['input_queries']['identifikasi_jenis_thematic_progression'] = pola_tp['identifikasi_jenis_thematic_progression']
    prompt = json.dumps(prompt, indent=4)
    problems_tp = llm(prompt)
    problems_tp = fix_json_if_incomplete(problems_tp)
    return problems_tp

def function_klasifikasi_logical_fallacies(respons, counter_example):
    prompt = load_prompt_template("klasifikasi_lf.json")
    prompt['context']['input_queries']['respons_chatbot'] = respons  
    prompt['context']['relevant_information']['counterexample'] = counter_example
    prompt = json.dumps(prompt, indent=4)
    logical_fallacy = llm(prompt)
    print(f"❇️ Hasil Klasifikasi Logical Fallacy: {logical_fallacy}")
    print()

    try:
        logical_fallacy = {
            'jenis': fix_json_if_incomplete(logical_fallacy)['logical_fallacy']['jenis'],
            'kalimat_teridentifikasi_logical_fallacy': fix_json_if_incomplete(logical_fallacy)['logical_fallacy']['kalimat_teridentifikasi_logical_fallacy']
        }
    except Exception as e:
        logical_fallacy = {
            'jenis': fix_json_if_incomplete(logical_fallacy)['jenis'],
            'kalimat_teridentifikasi_logical_fallacy': fix_json_if_incomplete(logical_fallacy)['kalimat_teridentifikasi_logical_fallacy']
        }
    return logical_fallacy

def function_perbaikan_respons_chatbot(respons_chatbot, counter_example, logical_fallacy, thematic_progression_problems):
    prompt = load_prompt_template("modifikasi.json")
    prompt['context']['relevant_information']['logical_fallacy'] = str(logical_fallacy)  
    prompt['context']['relevant_information']['counterexample'] = str(counter_example)
    prompt['context']['input_queries']['thematic_progression_problems'] = thematic_progression_problems
    prompt['context']['input_queries']['respons_chatbot'] = respons_chatbot
    prompt = json.dumps(prompt, indent=4)
    modifikasi_respons = llm(prompt)
    print(f"❇️ Hasil Modifikasi: {modifikasi_respons}")
    print()
    modifikasi_respons = {
        "kalimat_asli": fix_json_if_incomplete(modifikasi_respons)['kalimat_asli'],
        "kalimat_modifikasi": fix_json_if_incomplete(modifikasi_respons)['kalimat_modifikasi'],
        "kalimat_keseluruhan": fix_json_if_incomplete(modifikasi_respons)['kalimat_keseluruhan']
    }
    return modifikasi_respons
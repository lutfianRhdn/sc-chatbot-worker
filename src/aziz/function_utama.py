from functions_non_utama import load_prompt_template, llm, fix_json_if_incomplete
from get_counter_example import get_counter_example
import json

def transformasi_respons_chatbot_ke_fol(respons):
    chains = ["premis_kesimpulan.json", "terms.json", "atomic_formula.json", "fol.json"]

    for chain in chains:
        if chain == "premis_kesimpulan.json":
            prompt = load_prompt_template(chain)
            prompt['input_queries'] = respons
            prompt = json.dumps(prompt, indent=4)
            print()
            chain_1 = llm(prompt)
            print(f"Chain 1: {chain_1}")
        elif chain == "terms.json":
            prompt = load_prompt_template(chain)
            data = fix_json_if_incomplete(chain_1)
            print(f"Data after fix_json_if_incomplete: {data}")
            premis = data['premis']
            kesimpulan = data['kesimpulan']
            input_queries = {"premis": premis, "kesimpulan": kesimpulan}
            print(f"Input Queries: {str(input_queries)}")
            prompt['input_queries'] = str(input_queries)
            prompt = json.dumps(prompt, indent=4)
            chain_2 = llm(prompt)
            print(f"Chain 2: {chain_2}")
        elif chain == "atomic_formula.json":
            prompt = load_prompt_template(chain)
            data = fix_json_if_incomplete(chain_2)
            print(f"Data after fix_json_if_incomplete: {data}")
            term_premis = data['terms_premis']
            term_kesimpulan = data['terms_kesimpulan']
            print(f"Input Queries: {str(input_queries)}")
            prompt['context']['input_queries']['sentence'] = respons
            prompt['context']['input_queries']['term_premis'] = term_premis
            prompt['context']['input_queries']['term_kesimpulan'] = term_kesimpulan
            prompt = json.dumps(prompt, indent=4)
            print(f"Prompt for Atomic Formula: {prompt}")
            chain_3 = llm(prompt)
            print(f"Chain 3: {chain_3}")
        elif chain == "fol.json":
            prompt = load_prompt_template(chain)
            data_chain_1 = fix_json_if_incomplete(chain_1)
            data_chain_2 = fix_json_if_incomplete(chain_2)
            data_chain_3 = fix_json_if_incomplete(chain_3)
            print(f"Data after fix_json_if_incomplete: {data}")
            premis = data_chain_1['premis']
            kesimpulan = data_chain_1['kesimpulan']
            term_premis = data_chain_2['terms_premis']
            term_kesimpulan = data_chain_2['terms_kesimpulan']
            atomic_formula = data_chain_3['atomic_formula']
            prompt['context']['input_queries']['sentence'] = respons
            prompt['context']['input_queries']['premis'] = premis
            prompt['context']['input_queries']['kesimpulan'] = kesimpulan
            prompt['context']['input_queries']['term_premis'] = term_premis
            prompt['context']['input_queries']['term_kesimpulan'] = term_kesimpulan
            prompt['context']['input_queries']['atomic_formula'] = atomic_formula
            prompt = json.dumps(prompt, indent=4)
            chain_4 = llm(prompt)
            print(f"Chain 4: {chain_4}")
            fol_keseluruhan = fix_json_if_incomplete(chain_4)
            print(f"FOL Keseluruhan: {fol_keseluruhan['fol']}")
            fol_keseluruhan = fol_keseluruhan['fol']

    return chain_1, chain_2, chain_3, chain_4, fol_keseluruhan

def pembuatan_counter_example(respons, fol_keseluruhan):
    hasil_cvc5 = get_counter_example(fol_keseluruhan)
    prompt = load_prompt_template("interpretasi_counter_example.json")
    prompt['context']['kalimat_asli'] = respons
    prompt['context']['fol'] = fol_keseluruhan
    prompt['context']['input_queries_hasil_cvc5'] = hasil_cvc5
    prompt = json.dumps(prompt, indent=4)
    interpretasi_counter_example = llm(prompt)
    return interpretasi_counter_example

def klasifikasi_logical_fallacies(respons, counter_example):
    prompt = load_prompt_template("klasifikasi_lf.json")
    prompt['context']['respons_chatbot'] = respons  
    prompt['context']['counterexample'] = counter_example
    prompt = json.dumps(prompt, indent=4)
    logical_fallacy = llm(prompt)
    return logical_fallacy
import subprocess
from cvc import CVCGenerator
import re

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
        # print(f"Script SMT-LIB:\n{script}")
        # Menyimpan skrip SMT-LIB ke dalam file
        with open("logical_form.smt2", "w") as f:
            f.write(script)

        # Menjalankan CVC5 solver dan menangkap output
        proc = subprocess.run([r"D:\Kuliah\SKRIPSI\Uji Coba LLM LF\NL2FOL\NL2FOL-ziz\cvc5\bin\cvc5", "--lang", "smt2", "logical_form.smt2"], capture_output=True, text=True, check=True)
        proc_result = proc.stdout

        # Menyimpan hasil output solver ke file
        with open("logical_form_out.txt", "w") as f:
            f.write(proc_result)
        return proc_result
    
    except Exception as e:
        return f"Terjadi kesalahan: {e}"

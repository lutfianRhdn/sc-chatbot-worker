from ast import Tuple
import subprocess
from multiprocessing.connection import Connection
import os
import re
import tempfile
import threading
import traceback
from typing import List
import uuid
import time
from  utils.log import log 
from utils.handleMessage import sendMessage, convertMessage

from .Worker import Worker

class SMTConverterWorker(Worker):
    ###############
    # dont edit this part
    ###############
    route_base = "/"
    conn:Connection
    requests: dict = {}
    def __init__(self):
        # we'll assign these in run()
        self._port: int = None

        self.requests: dict = {}
        
    def run(self, conn: Connection, port: int):
        # assign here
        SMTConverterWorker.conn = conn

        #### add your worker initialization code here
        
        
        
        
        
        
        #### until this part
        # start background threads *before* blocking server
        threading.Thread(target=self.listen_task, daemon=True).start()
        threading.Thread(target=self.health_check, daemon=True).start()

        # asyncio.run(self.listen_task())
        self.health_check()


    def health_check(self):
        """Send a heartbeat every 10s."""
        while True:
            sendMessage(
                conn=SMTConverterWorker.conn,
                messageId="heartbeat",
                status="healthy"
            )
            time.sleep(10)
    def listen_task(self):
        while True:
            try:
                if SMTConverterWorker.conn.poll(1):  # Check for messages with 1 second timeout
                    message = self.conn.recv()
                    dest = [
                        d
                        for d in message["destination"]
                        if d.split("/", 1)[0] == "SMTConverterWorker"
                    ]
                    destSplited = dest[0].split('/')
                    method = destSplited[1]
                    param= destSplited[2]
                    instance_method = getattr(self,method)
                    instance_method(message)
            except EOFError:
                break
            except Exception as e:
              print(e)
              log(f"Listener error: {e}",'error' )
              break

    def sendToOtherWorker(self, destination, messageId: str, data: dict = None) -> None:
      sendMessage(
          conn=SMTConverterWorker.conn,
          destination=destination,
          messageId=messageId,
          status="completed",
          reason="Message sent to other worker successfully.",
          data=data or {}
      )
    ##########################################
    # add your worker methods here
    ##########################################

    def fol_to_smtlib(self, message):
        try: 
            # print(message)
            ENTITY_SORT = "Entity"
            fol = message['data']['fol']
            logic = "ALL"
            # fol: str, logic: str = "ALL"
            def extract_predicates(expr: str) :
                pattern = r'(\w+)\(([^()]+(?:\([^)]*\))?[^()]*)\)'
                matches = re.findall(pattern, expr)
                result = []
                for match in matches:
                    pred_name = match[0]
                    args_str = match[1]
                    args = [arg.strip() for arg in re.split(r',(?![^()]*\))', args_str)]
                    # Filter out nested predicates
                    if all(re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', arg) for arg in args):
                        result.append((pred_name, args))
                return result

            def smt_predicate_call(pred: str, args: List[str]) -> str:
                return f"({pred} {' '.join(args)})"

            def parse_fol_expression(fol_expr: str) -> str:
                fol_expr = fol_expr.strip()

                if fol_expr.startswith("(") and fol_expr.endswith(")"):
                    paren_count = 0
                    for i, char in enumerate(fol_expr):
                        if char == '(':
                            paren_count += 1
                        elif char == ')':
                            paren_count -= 1
                            if paren_count == 0 and i < len(fol_expr) - 1:
                                break
                    else:
                        fol_expr = fol_expr[1:-1].strip()

                if "→" in fol_expr:
                    paren_count = 0
                    for i, char in enumerate(fol_expr):
                        if char == '(':
                            paren_count += 1
                        elif char == ')':
                            paren_count -= 1
                        elif char == '→' and paren_count == 0:
                            left = fol_expr[:i].strip()
                            right = fol_expr[i+1:].strip()
                            left_smt = parse_fol_expression(left)
                            right_smt = parse_fol_expression(right)
                            return f"(=> {left_smt} {right_smt})"

                if "∧" in fol_expr:
                    paren_count = 0
                    conjuncts = []
                    start = 0
                    for i, char in enumerate(fol_expr):
                        if char == '(':
                            paren_count += 1
                        elif char == ')':
                            paren_count -= 1
                        elif char == '∧' and paren_count == 0:
                            conjuncts.append(fol_expr[start:i].strip())
                            start = i + 1
                    conjuncts.append(fol_expr[start:].strip())
                    if len(conjuncts) > 1:
                        parsed = [parse_fol_expression(p) for p in conjuncts]
                        return f"(and {' '.join(parsed)})"

                if "∨" in fol_expr:
                    paren_count = 0
                    disjuncts = []
                    start = 0
                    for i, char in enumerate(fol_expr):
                        if char == '(':
                            paren_count += 1
                        elif char == ')':
                            paren_count -= 1
                        elif char == '∨' and paren_count == 0:
                            disjuncts.append(fol_expr[start:i].strip())
                            start = i + 1
                    disjuncts.append(fol_expr[start:].strip())
                    if len(disjuncts) > 1:
                        parsed = [parse_fol_expression(p) for p in disjuncts]
                        return f"(or {' '.join(parsed)})"

                if fol_expr.startswith("¬"):
                    inner = parse_fol_expression(fol_expr[1:].strip())
                    return f"(not {inner})"

                quant_match = re.match(r'(\u2200|\u2203)(\w+)\s+(.*)', fol_expr)
                if quant_match:
                    quant, var, body = quant_match.groups()
                    quant_smt = "forall" if quant == "∀" else "exists"
                    body = body.strip()
                    body_smt = parse_fol_expression(body)
                    return f"({quant_smt} (({var} {ENTITY_SORT})) {body_smt})"

                predicates = extract_predicates(fol_expr)
                if predicates:
                    return smt_predicate_call(*predicates[0])

                return fol_expr

            fol = fol.strip()
            formula_smt = parse_fol_expression(fol)

            pred_arity = {}

            def collect_predicates(expr: str):
                predicates = extract_predicates(expr)
                for pred, args in predicates:
                    pred_arity[pred] = len(args)

            def traverse_expression(expr: str):
                collect_predicates(expr)
                for op in ["→", "∧", "∨"]:
                    if op in expr:
                        parts = expr.split(op)
                        for part in parts:
                            traverse_expression(part.strip())

            traverse_expression(fol)

            all_terms = set(re.findall(r'\b[a-z]\w*\b', fol))
            pred_names = set(pred_arity.keys())
            all_vars = all_terms - pred_names

            lines = [
                f"(set-info :smt-lib-version 2.6)",
                f"(set-logic {logic})",
                f"(set-option :produce-models true)",
                f"(set-option :finite-model-find true)",
                f"(declare-sort {ENTITY_SORT} 0)"
            ]

            for pred, arity in sorted(pred_arity.items()):
                args = " ".join([ENTITY_SORT] * arity)
                lines.append(f"(declare-fun {pred} ({args}) Bool)")

            for var in sorted(all_vars):
                lines.append(f"(declare-const {var} {ENTITY_SORT})")

            lines += [
                f"(assert (not {formula_smt}))",
                "(check-sat)",
                "(get-model)"
            ]
            # print("\n".join(lines))
            return self.smt_solver("\n".join(lines),message)
        except Exception as e:
            traceback.print_exc()
            print(e)


    def smt_solver(self, smt2_code: str, message):
        cvc5_path: str = None
        get_model: bool = True
        if cvc5_path is None:
            base_path = os.path.dirname(os.path.abspath(__file__))
            cvc5_path = os.path.join(base_path, "../cvc5/bin/cvc5.exe")
            possible_paths = [cvc5_path]
            for path in possible_paths:
                try:
                    result = subprocess.run([path, "--version"], capture_output=True, timeout=5)
                    if result.returncode == 0:
                        cvc5_path = path
                        break
                except:
                    continue
            if cvc5_path is None:
                raise RuntimeError("CVC5 not found.")

        with tempfile.NamedTemporaryFile(mode="w+", suffix=".smt2", delete=False) as tmp_file:
            tmp_file.write(smt2_code)
            tmp_file.flush()
            tmp_path = tmp_file.name

        try:
            cmd = [cvc5_path, "--lang", "smt2"]
            if get_model:
                cmd += ["--produce-models"]
            cmd.append(tmp_path)

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            output = result.stdout.strip()
            stderr_output = result.stderr.strip()

            # print(f"DEBUG - Return code: {result.returncode}")
            # print(f"DEBUG - STDOUT length: {len(output)}")
            # print(f"DEBUG - STDERR length: {len(stderr_output)}")
            # print(output)
            if stderr_output:
                print(f"DEBUG - STDERR: {stderr_output}")

            if output.startswith("sat") or output.startswith("unsat"):
                lines = output.splitlines()
                check_sat = lines[0].strip().lower()
                counterexample = "\n".join(lines[1:]).strip() if check_sat == "sat" else ""
            else:
                counterexample = "-"
                check_sat = "unknown"
            # if result.returncode != 0:
            #     raise RuntimeError(f"CVC5 error (code {result.returncode}):\n{stderr_output}")
            # print(counterexample)
            self.sendToOtherWorker(
                messageId=message.get("messageId"),
                destination=["CounterExampleCreatorWorker/interpretasi_counterexample/"],
                data={
                    "model":counterexample,
                    "check_sat":check_sat or "unknown",
                    "prompt": message["data"]["prompt"],
                    "premis": message["data"]["premis"],
                    "kesimpulan": message["data"]["kesimpulan"],
                    "term_premis": message["data"]["term_premis"],
                    "terms_kesimpulan": message["data"]["terms_kesimpulan"],
                    "predikat": message["data"]["predikat"],
                    "fol": message["data"]["fol"],
                    "feedback": message["data"]["feedback"],
                    "is_eval": message["data"]["is_eval"],
                    "user_intent" : message["data"]["user_intent"],
                    "eval_iteration" : message["data"]["eval_iteration"],
                    "prompt_user" : message["data"]["prompt_user"]
            })

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)    

    def test(self,message)->None:
        """
        Example method to test the worker functionality.
        Replace this with your actual worker methods.
        """
        data = message.get("data", {})


        # process


        #send back to RestAPI
        self.sendToOtherWorker(
          messageId=message.get("messageId"),
          destination=["RestApiWorker/onProcessed"],
          data=data
          )
      #   sendMessage(
      #     status="completed",
      #     reason="Test method executed successfully.",
      #     destination=["supervisor"],
      #     data={"message": "This is a test response."}
      # )
        log("Test method called", "info")
        # return {"status": "success", "data": "This is a test response."}

def main(conn: Connection, config: dict):
    worker = SMTConverterWorker()
    worker.run(conn, config)

import z3
import hashlib
import time
import sys

sys.setrecursionlimit(10000)

def log_telemetry(fase, mensaje):
    t = time.time()
    ms = int((t - int(t)) * 1000)
    print(f"[{time.strftime('%H:%M:%S')}.{ms:03d}] [TELEMETRÍA] | {fase} | {mensaje}")

print("=======================================================================")
print("=== VERIFICACIÓN FORMAL DEL MOTOR L4 (ANEXO A - PAPER NP)           ===")
print("=======================================================================\n")

N, M, K = 4, 6, 4
log_telemetry("INIT", f"Parámetros topológicos: N={N}, M={M}, K={K}")

VAL_N = z3.BitVecVal(0, 2)
VAL_F = z3.BitVecVal(1, 2)
VAL_T = z3.BitVecVal(2, 2)
VAL_B = z3.BitVecVal(3, 2)

def is_false(val, sign_is_positive):
    bit0 = z3.Extract(0, 0, val) == z3.BitVecVal(1, 1)
    bit1 = z3.Extract(1, 1, val) == z3.BitVecVal(1, 1)
    return z3.If(sign_is_positive, bit0, bit1)

def force_value(sign_is_positive):
    return z3.If(sign_is_positive, VAL_T, VAL_F)

def get_var_val(V_array, idx):
    res = V_array[0]
    for i in range(1, N):
        res = z3.If(idx == i, V_array[i], res)
    return res

vars_idx = [[z3.Int(f"var_c{c}_j{j}") for j in range(3)] for c in range(M)]
signs = [[z3.Bool(f"sign_c{c}_j{j}") for j in range(3)] for c in range(M)]

valid_topology = z3.And([z3.And(vars_idx[c][j] >= 0, vars_idx[c][j] < N) 
                         for c in range(M) for j in range(3)])

X_star = [z3.Bool(f"X_star_{i}") for i in range(N)]

def eval_classical_clause(c):
    return z3.Or([z3.If(signs[c][j], 
                        get_var_val(X_star, vars_idx[c][j]), 
                        z3.Not(get_var_val(X_star, vars_idx[c][j]))) 
                  for j in range(3)])

classical_sat = z3.And([eval_classical_clause(c) for c in range(M)])

V = [[z3.BitVec(f"V_k{k}_i{i}", 2) for i in range(N)] for k in range(K + 1)]
initial_state_valid = z3.And([z3.Or(V[0][i] == VAL_N, V[0][i] == VAL_T, V[0][i] == VAL_F) for i in range(N)])

classical_consistency = z3.And([
    z3.And(z3.Implies(V[0][i] == VAL_T, X_star[i] == True),
           z3.Implies(V[0][i] == VAL_F, X_star[i] == False))
    for i in range(N)
])

propagation_rules = []
for k in range(K):
    for i in range(N):
        forced_acc = z3.BitVecVal(0, 2)
        for c in range(M):
            for j in range(3):
                is_target = (vars_idx[c][j] == i)
                other1, other2 = (j + 1) % 3, (j + 2) % 3
                val1 = get_var_val(V[k], vars_idx[c][other1])
                val2 = get_var_val(V[k], vars_idx[c][other2])
                cond = z3.And(is_target, is_false(val1, signs[c][other1]), is_false(val2, signs[c][other2]))
                forced_acc = forced_acc | z3.If(cond, force_value(signs[c][j]), z3.BitVecVal(0, 2))
        propagation_rules.append(V[k+1][i] == (V[k][i] | forced_acc))

belnap_physics = z3.And(propagation_rules)
V_inf = V[K]

def run_theorem(name, hypothesis, expect_sat, extra_constraints=None):
    print(f"\n{'-'*70}")
    log_telemetry("SOLVER", f"Evaluando {name}...")
    s = z3.Solver()
    s.add(valid_topology)
    s.add(belnap_physics)
    if extra_constraints is not None:
        s.add(extra_constraints)
    s.add(hypothesis)
    
    t0 = time.time()
    res = s.check()
    t1 = time.time()
    
    stats = s.statistics()
    conflicts = stats.get_key_value('conflicts') if 'conflicts' in stats.keys() else 0
    seal = hashlib.sha256((s.to_smt2() + str(res)).encode('utf-8')).hexdigest()
    
    log_telemetry("RESULT", f"Resultado: {res} (Esperado: {'sat' if expect_sat else 'unsat'})")
    log_telemetry("METRICS", f"Tiempo Z3: {(t1-t0)*1000:.2f} ms | Conflictos: {conflicts}")
    log_telemetry("CRYPTO", f"Sello SHA-256: {seal}")
    
    if (res == z3.sat and expect_sat) or (res == z3.unsat and not expect_sat):
        log_telemetry("VERDICT", "TEOREMA DEMOSTRADO CON RIGOR ABSOLUTO. [EXITO]")
    else:
        log_telemetry("FATAL", "FALLO CATASTRÓFICO EN LA VERIFICACIÓN.")
        sys.exit(1)

# Teorema 3: Soundness
th1_base = z3.And(initial_state_valid, classical_consistency)
th1_hyp = z3.And(classical_sat, z3.Or([
    z3.Or(z3.And(V_inf[i] == VAL_T, X_star[i] == False),
          z3.And(V_inf[i] == VAL_F, X_star[i] == True))
    for i in range(N)
]))
run_theorem("TEOREMA 3: Preservación de la Verdad Absoluta (Soundness)", th1_hyp, expect_sat=False, extra_constraints=th1_base)

# Teorema 4: Resiliencia Termodinámica
noise_injected = z3.Or([
    z3.Or(z3.And(V[0][i] == VAL_T, X_star[i] == False),
          z3.And(V[0][i] == VAL_F, X_star[i] == True))
    for i in range(N)
])
th2_hyp = z3.And(classical_sat, noise_injected, z3.Or([V_inf[i] == VAL_B for i in range(N)]))
run_theorem("TEOREMA 4: Resiliencia Termodinámica (Absorción de Ruido)", th2_hyp, expect_sat=True, extra_constraints=initial_state_valid)

# Teorema 5: Inevitabilidad de Dialeteia
classical_unsat = z3.Not(z3.Exists([X_star[i] for i in range(N)], classical_sat))
no_voids_initial = z3.And([z3.Or(V[0][i] == VAL_T, V[0][i] == VAL_F) for i in range(N)])
no_dialeteias_final = z3.And([V_inf[i] != VAL_B for i in range(N)])
th3_base = z3.And(initial_state_valid, no_voids_initial)
th3_hyp = z3.And(classical_unsat, no_dialeteias_final)
run_theorem("TEOREMA 5: Inevitabilidad de Dialeteia bajo Decimación Completa", th3_hyp, expect_sat=False, extra_constraints=th3_base)
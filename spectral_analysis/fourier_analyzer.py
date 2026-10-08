import numpy as np
import matplotlib.pyplot as plt
import time
import hashlib
import os

N = 14
M = 25
NUM_STATES = 1 << N

print("=======================================================================")
print("=== ESPECTRÓMETRO DE WALSH-FOURIER: TEOREMA LMN (ANEXO E)           ===")
print("=======================================================================\n")

np.random.seed(42)
clauses = []
for _ in range(M):
    vars_idx = np.random.choice(range(1, N + 1), 3, replace=False)
    signs = np.random.choice([-1, 1], 3)
    clauses.append(vars_idx * signs)

def evaluate_circuit(state_int):
    bits = [(state_int >> i) & 1 for i in range(N)]
    for clause in clauses:
        clause_sat = False
        for lit in clause:
            var_idx = abs(lit) - 1
            val = bits[var_idx]
            if (lit > 0 and val == 1) or (lit < 0 and val == 0):
                clause_sat = True
                break
        if not clause_sat:
            return 0
    return 1

print("[*] Evaluando tabla de verdad...")
truth_table = np.array([1.0 if evaluate_circuit(i) == 0 else -1.0 for i in range(NUM_STATES)], dtype=np.float64)

def fwht(a):
    h = 1
    while h < len(a):
        for i in range(0, len(a), h * 2):
            for j in range(i, i + h):
                x, y = a[j], a[j + h]
                a[j] = x + y
                a[j + h] = x - y
        h *= 2
    return a

print("[*] Ejecutando FWHT...")
fourier_coeffs = fwht(truth_table.copy()) / NUM_STATES

# Teorema de Parseval
total_energy = np.sum(fourier_coeffs**2)
assert np.isclose(total_energy, 1.0, atol=1e-9), "Violación de Parseval."

energy_by_degree = np.zeros(N + 1, dtype=np.float64)
for i in range(NUM_STATES):
    degree = bin(i).count('1')
    energy_by_degree[degree] += fourier_coeffs[i]**2

seal = hashlib.sha256(energy_by_degree.tobytes()).hexdigest()
print(f"[*] Sello SHA-256 del Espectro: {seal}")

cumulative_energy = np.cumsum(energy_by_degree) * 100.0
cutoff_degree = 4
low_degree_energy = cumulative_energy[cutoff_degree]

fig, ax1 = plt.subplots(figsize=(10, 6))
degrees = np.arange(N + 1)
ax1.bar(degrees, energy_by_degree * 100.0, color='purple', alpha=0.7, label='Masa Espectral por Grado (%)')
ax1.set_xlabel('Grado Polinómico (k)', fontsize=12)
ax1.set_ylabel('Energía (%)', fontsize=12, color='purple')

ax2 = ax1.twinx()
ax2.plot(degrees, cumulative_energy, 'ro-', linewidth=2, label='Energía Acumulada (%)')
ax2.set_ylabel('Acumulada (%)', fontsize=12, color='red')
ax2.axvline(x=cutoff_degree + 0.5, color='black', linestyle='--', label=f'Corte D={cutoff_degree}')

plt.title('Espectrometría Walsh-Fourier: Concentración LMN', fontsize=14, fontweight='bold')
output_path = os.path.join(os.path.dirname(__file__), "espectro_fourier_lmn.png")
plt.savefig(output_path, dpi=300)
print(f"[Q.E.D.] Radiografía generada: {output_path}")
print(f"[*] El {low_degree_energy:.2f}% de la energía algorítmica reside en grado <= {cutoff_degree}.")
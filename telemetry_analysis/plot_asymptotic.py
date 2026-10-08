import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import sys

targets = [
    {"N": 50, "csv": "telemetria_50.csv"},
    {"N": 100, "csv": "telemetria_100.csv"},
    {"N": 150, "csv": "telemetria_150.csv"}
]

results_N = []
results_backtracks = []

for t in targets:
    if os.path.exists(t["csv"]):
        df = pd.read_csv(t["csv"])
        bt = len(df[df['Action'] == 'BACKTRACK'])
        results_N.append(t["N"])
        results_backtracks.append(bt)
    else:
        print(f"[FATAL] Falta {t['csv']}. Corre el Megakernel primero.")
        sys.exit(1)

N_arr = np.array(results_N)
log2_bt = np.log2(np.array(results_backtracks))

# Pendiente promedio gamma
gamma_1 = (log2_bt[1] - log2_bt[0]) / (N_arr[1] - N_arr[0])
gamma_2 = (log2_bt[2] - log2_bt[1]) / (N_arr[2] - N_arr[1])
gamma = (gamma_1 + gamma_2) / 2.0

coef = np.polyfit(N_arr, log2_bt, 1)
C = 2**coef[1]

fig, ax = plt.subplots(figsize=(10, 6))
ax.set_yscale('log')
ax.plot(results_N, results_backtracks, 'ro-', linewidth=2.5, markersize=8, label='Datos Empíricos (GPU Ampere)')

N_trend = np.linspace(40, 160, 100)
ax.plot(N_trend, C * (2**(gamma * N_trend)), 'k--', linewidth=2, label=f'Ajuste Exponencial $O(2^{{{gamma:.4f} N}})$')

ax.set_xlabel('Variables Lógicas ($N$)', fontsize=12)
ax.set_ylabel('Backtracks (Escala Logarítmica)', fontsize=12, color='darkred')
ax.grid(True, which="both", ls="--", alpha=0.5)
ax.legend(loc='upper left')

for i, txt in enumerate(results_backtracks):
    ax.annotate(f"{txt:,}", (results_N[i], results_backtracks[i]), textcoords="offset points", xytext=(0, 10), ha='center', fontweight='bold')

plt.tight_layout()
output_img = "curva_asintotica_milenio.png"
plt.savefig(output_img, dpi=300)
print(f"[Q.E.D.] Figura 3 generada con éxito: {output_img} (gamma = {gamma:.4f})")
import pandas as pd
import matplotlib.pyplot as plt
import sys
import os

if len(sys.argv) != 3:
    print("Uso: python plot_thermodynamics.py <archivo.csv> <figura_salida.png>")
    sys.exit(1)

csv_path = sys.argv[1]
output_img = sys.argv[2]

if not os.path.exists(csv_path):
    print(f"[FATAL] No se encontró el archivo {csv_path}")
    sys.exit(1)

df = pd.read_csv(csv_path)

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

# 1. Árbol de Búsqueda (Profundidad vs Tiempo)
ax1.plot(df.index, df['Depth'], color='blue', linewidth=0.8, label='Profundidad de Decimación')
backtracks = df[df['Action'] == 'BACKTRACK']
if not backtracks.empty:
    ax1.scatter(backtracks.index, backtracks['Depth'], color='red', s=8, alpha=0.8, label='Backtrack (Choque OGP)')
ax1.set_title('Navegación del Espacio de Fases (Árbol Termodinámico)', fontsize=12, fontweight='bold')
ax1.set_ylabel('Profundidad')
ax1.grid(True, linestyle='--', alpha=0.6)
ax1.legend(loc='upper left')

# 2. Firma OGP (Variables en B y N)
ax2.plot(df.index, df['Vars_N'], color='gray', linewidth=1.0, label='Variables en N (Paramagnético)')
ax2.plot(df.index, df['Vars_B'], color='purple', linewidth=1.0, label='Variables en B (Dialeteia / Entropía)')
ax2.set_title('Firma de la Brecha de Superposición (OGP)', fontsize=12, fontweight='bold')
ax2.set_xlabel('Eventos (Iteraciones del Host)')
ax2.set_ylabel('Cantidad de Variables')
ax2.grid(True, linestyle='--', alpha=0.6)
ax2.legend(loc='upper right')

plt.tight_layout()
plt.savefig(output_img, dpi=300)
print(f"[Q.E.D.] Radiografía generada: {output_img}")
@echo off
echo =======================================================================
echo === INICIANDO PIPELINE MAESTRO: TERMODINAMICA DE LA CLASE NP        ===
echo =======================================================================

echo [1/6] Instalando dependencias de Python...
pip install -r requirements.txt

echo [2/6] Ejecutando Verificacion Formal Z3 (Anexo A)...
python formal_verification/z3_sat_equivalence.py

echo [3/6] Ejecutando Espectrometro de Fourier LMN (Anexo E)...
python spectral_analysis/fourier_analyzer.py

echo [4/6] Descargando instancias de SATLIB...
python benchmarks/download_satlib.py

echo [5/6] Compilando e invocando Compilador Topologico HDC (Rust)...
cd hdc_compiler
cargo build --release
cd ..
hdc_compiler\target\release\hdc_compiler.exe benchmarks\data\subcritical_100.cnf payload_sub.bin
hdc_compiler\target\release\hdc_compiler.exe benchmarks\data\uuf50-01.cnf payload_50.bin
hdc_compiler\target\release\hdc_compiler.exe benchmarks\data\uuf100-01.cnf payload_100.bin
hdc_compiler\target\release\hdc_compiler.exe benchmarks\data\uuf150-01.cnf payload_150.bin

echo [6/6] Compilando Megakernel CUDA (Ampere sm_86)...
cd cuda_megakernel
call build_megakernel.bat
cd ..
copy cuda_megakernel\godel_megakernel.exe .

echo === LANZANDO EVALUACION TERMODINAMICA EN SILICIO ===
godel_megakernel.exe payload_sub.bin telemetria_sub.csv
godel_megakernel.exe payload_50.bin telemetria_50.csv
godel_megakernel.exe payload_100.bin telemetria_100.csv
echo [*] Evaluando N=150 (tomara algunos minutos debido al muro OGP)...
godel_megakernel.exe payload_150.bin telemetria_150.csv

echo === GENERANDO RADIOGRAFIAS DEL PAPER ===
python telemetry_analysis/plot_thermodynamics.py telemetria_sub.csv figura_1_fase_liquida.png
python telemetry_analysis/plot_thermodynamics.py telemetria_100.csv figura_2_umbral_critico.png
python telemetry_analysis/plot_asymptotic.py

echo =======================================================================
echo [Q.E.D.] PIPELINE COMPLETO FINALIZADO. REVISA TUS GRAFICAS GENERADAS.
echo =======================================================================
pause
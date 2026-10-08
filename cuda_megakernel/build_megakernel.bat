@echo off
if not defined VSCMD_ARG_TGT_ARCH call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat" -vcvars_ver=14.44
if not defined VSCMD_ARG_TGT_ARCH call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"

nvcc -ccbin "cl.exe" -O3 -arch=sm_86 -use_fast_math -std=c++17 -Xcompiler "/Zc:preprocessor /openmp /wd4068" godel_megakernel.cu -o godel_megakernel.exe
if %ERRORLEVEL% EQU 0 (
    echo [EXITO] Binario compilado: godel_megakernel.exe
) else (
    echo [FATAL] Error en la compilacion CUDA.
)
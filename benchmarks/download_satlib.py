import os
import urllib.request
import tarfile
import random

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

BENCHMARKS = {
    "uuf50-01.cnf": "https://www.cs.ubc.ca/~hoos/SATLIB/Benchmarks/SAT/RND3SAT/uuf50-218.tar.gz",
    "uuf100-01.cnf": "https://www.cs.ubc.ca/~hoos/SATLIB/Benchmarks/SAT/RND3SAT/uuf100-430.tar.gz",
    "uuf150-01.cnf": "https://www.cs.ubc.ca/~hoos/SATLIB/Benchmarks/SAT/RND3SAT/uuf150-645.tar.gz"
}

def download_and_extract(filename, url):
    target_path = os.path.join(DATA_DIR, filename)
    if os.path.exists(target_path):
        print(f"[*] Instancia ya presente: {filename}")
        return

    tar_path = os.path.join(DATA_DIR, "temp.tar.gz")
    print(f"[*] Descargando desde SATLIB: {url}...")
    urllib.request.urlretrieve(url, tar_path)
    
    with tarfile.open(tar_path, "r:gz") as tar:
        for member in tar.getmembers():
            if member.name.endswith(".cnf"):
                f = tar.extractfile(member)
                with open(target_path, "wb") as out:
                    out.write(f.read())
                print(f"[+] Extraido exitosamente: {filename}")
                break
    os.remove(tar_path)

def generate_subcritical(filename, n=100, alpha=3.0):
    """Genera una instancia en fase liquida (lejos de la OGP) para Figura 1."""
    target_path = os.path.join(DATA_DIR, filename)
    if os.path.exists(target_path):
        return
    m = int(n * alpha)
    print(f"[*] Generando instancia sub-critica (N={n}, M={m}, alpha={alpha})...")
    random.seed(42)
    with open(target_path, "w") as f:
        f.write(f"c Instancia sub-critica sintetica para Fase Liquida\np cnf {n} {m}\n")
        for _ in range(m):
            vars_chosen = random.sample(range(1, n + 1), 3)
            clause = [v if random.random() > 0.5 else -v for v in vars_chosen]
            f.write(f"{clause[0]} {clause[1]} {clause[2]} 0\n")
    print(f"[+] Generada instancia sub-critica: {filename}")

if __name__ == "__main__":
    print("=== DESCARGANDO MUNICIóN SATLIB OFICIAL ===")
    for fname, url in BENCHMARKS.items():
        download_and_extract(fname, url)
    generate_subcritical("subcritical_100.cnf", n=100, alpha=3.0)
    print("=== BANCO DE PRUEBAS COMPLETO ===")
use rand::{Rng, SeedableRng};
use rand_chacha::ChaCha8Rng;
use std::env;
use std::fs::File;
use std::io::{BufRead, BufReader, Write};
use std::time::Instant;

pub const HDC_U32_LEN: usize = 320; // 10240 bits / 32 bits por palabra

#[derive(Clone, Copy)]
pub struct Hypervector {
    pub data: [u32; HDC_U32_LEN],
}

impl Hypervector {
    pub fn new_orthogonal(rng: &mut ChaCha8Rng) -> Self {
        let mut data = [0u32; HDC_U32_LEN];
        for i in 0..HDC_U32_LEN {
            data[i] = rng.gen::<u32>();
        }
        Hypervector { data }
    }

    pub fn bind(&self, other: &Hypervector) -> Self {
        let mut result = [0u32; HDC_U32_LEN];
        for i in 0..HDC_U32_LEN {
            result[i] = self.data[i] ^ other.data[i];
        }
        Hypervector { data: result }
    }

    pub fn bundle_majority(a: &Hypervector, b: &Hypervector, c: &Hypervector) -> Self {
        let mut result = [0u32; HDC_U32_LEN];
        for i in 0..HDC_U32_LEN {
            result[i] = (a.data[i] & b.data[i]) | (a.data[i] & c.data[i]) | (b.data[i] & c.data[i]);
        }
        Hypervector { data: result }
    }
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() != 3 {
        eprintln!("Uso: hdc_compiler <entrada.cnf> <salida.bin>");
        std::process::exit(1);
    }

    let input_path = &args[1];
    let output_path = &args[2];

    println!("=======================================================");
    println!("=== COMPILADOR TOPOLÓGICO HDC (ANEXO B)             ===");
    println!("=======================================================");

    let file = File::open(input_path).expect("No se pudo abrir el archivo CNF.");
    let reader = BufReader::new(file);

    let mut num_vars = 0u32;
    let mut num_clauses = 0u32;
    let mut explicit_clauses: Vec<[i32; 3]> = Vec::new();

    for line in reader.lines() {
        let line = line.unwrap();
        let trimmed = line.trim();
        if trimmed.starts_with('c') || trimmed.is_empty() { continue; }
        if trimmed.starts_with('%') { break; } // Escudo SATLIB

        if trimmed.starts_with('p') {
            let parts: Vec<&str> = trimmed.split_whitespace().collect();
            num_vars = parts[2].parse().unwrap();
            num_clauses = parts[3].parse().unwrap();
            continue;
        }

        let parts: Vec<&str> = trimmed.split_whitespace().collect();
        if parts.len() >= 3 {
            let c = [
                parts[0].parse::<i32>().unwrap(),
                parts[1].parse::<i32>().unwrap(),
                parts[2].parse::<i32>().unwrap(),
            ];
            explicit_clauses.push(c);
        }
    }

    println!("[*] Parseado: N={}, Cláusulas={}", num_vars, explicit_clauses.len());

    let mut rng = ChaCha8Rng::seed_from_u64(42);
    let mut var_tensors = Vec::with_capacity(num_vars as usize);
    for _ in 0..num_vars {
        var_tensors.push(Hypervector::new_orthogonal(&mut rng));
    }
    let r_pos = Hypervector::new_orthogonal(&mut rng);
    let r_neg = Hypervector::new_orthogonal(&mut rng);

    let mut clause_tensors = Vec::with_capacity(explicit_clauses.len());
    let t_cryst = Instant::now();
    for clause in &explicit_clauses {
        let get_lit = |lit: i32| {
            let v = (lit.abs() - 1) as usize;
            let role = if lit > 0 { &r_pos } else { &r_neg };
            var_tensors[v].bind(role)
        };
        clause_tensors.push(Hypervector::bundle_majority(
            &get_lit(clause[0]),
            &get_lit(clause[1]),
            &get_lit(clause[2]),
        ));
    }
    println!("[*] Cristalización HDC completada en {:.2?}", t_cryst.elapsed());

    let mut out = File::create(output_path).expect("Error creando payload binario.");
    out.write_all(&num_vars.to_le_bytes()).unwrap();
    let actual_clauses = explicit_clauses.len() as u32;
    out.write_all(&actual_clauses.to_le_bytes()).unwrap();

    for t in &var_tensors {
        for &w in &t.data { out.write_all(&w.to_le_bytes()).unwrap(); }
    }
    for t in &clause_tensors {
        for &w in &t.data { out.write_all(&w.to_le_bytes()).unwrap(); }
    }
    for c in &explicit_clauses {
        for &lit in c { out.write_all(&lit.to_le_bytes()).unwrap(); }
    }
    println!("[Q.E.D.] Payload exportado a: {}", output_path);
}
// ============================================================================
// MEGAKERNEL TERMODINÁMICO L4 + PROTOCOLO DE DECIMACIÓN (RTX 3050 Ti sm_86)
// ============================================================================

#include <cuda_runtime.h>
#include <iostream>
#include <fstream>
#include <vector>
#include <chrono>

#define VAL_N 0 // 00 (Void)
#define VAL_F 1 // 01 (False)
#define VAL_T 2 // 10 (True)
#define VAL_B 3 // 11 (Dialeteia)

__device__ inline int is_false_l4(int literal, uint32_t state_word) {
    int var_idx = abs(literal) - 1;
    int bit_shift = (var_idx % 16) * 2;
    uint32_t var_state = (state_word >> bit_shift) & 0b11;
    if (literal > 0) return (var_state & 1);
    else return ((var_state >> 1) & 1);
}

__device__ inline uint32_t get_force_mask(int literal) {
    int var_idx = abs(literal) - 1;
    int bit_shift = (var_idx % 16) * 2;
    uint32_t sign_val = (literal > 0) ? VAL_T : VAL_F;
    return sign_val << bit_shift;
}

__global__ void godel_coinductive_kernel(
    const int* explicit_clauses, 
    uint32_t* global_state,      
    int num_clauses,
    int num_vars,
    unsigned long long* telemetry_cycles,
    int* changes_detected
) {
    unsigned long long start_time = clock64();
    extern __shared__ uint32_t shared_state[];
    int state_ints = (num_vars + 15) / 16;

    for (int i = threadIdx.x; i < state_ints; i += blockDim.x) {
        shared_state[i] = global_state[i];
    }
    __syncthreads();

    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    int local_changes = 0;
    
    if (tid < num_clauses) {
        int l1 = explicit_clauses[tid * 3 + 0];
        int l2 = explicit_clauses[tid * 3 + 1];
        int l3 = explicit_clauses[tid * 3 + 2];

        uint32_t word1 = shared_state[(abs(l1) - 1) / 16];
        uint32_t word2 = shared_state[(abs(l2) - 1) / 16];
        uint32_t word3 = shared_state[(abs(l3) - 1) / 16];

        int f1 = is_false_l4(l1, word1);
        int f2 = is_false_l4(l2, word2);
        int f3 = is_false_l4(l3, word3);

        if (f2 & f3) {
            uint32_t old = atomicOr(&shared_state[(abs(l1) - 1) / 16], get_force_mask(l1));
            if ((old & get_force_mask(l1)) != get_force_mask(l1)) local_changes = 1;
        }
        if (f1 & f3) {
            uint32_t old = atomicOr(&shared_state[(abs(l2) - 1) / 16], get_force_mask(l2));
            if ((old & get_force_mask(l2)) != get_force_mask(l2)) local_changes = 1;
        }
        if (f1 & f2) {
            uint32_t old = atomicOr(&shared_state[(abs(l3) - 1) / 16], get_force_mask(l3));
            if ((old & get_force_mask(l3)) != get_force_mask(l3)) local_changes = 1;
        }
    }
    __syncthreads();

    for (int i = threadIdx.x; i < state_ints; i += blockDim.x) {
        uint32_t current_val = global_state[i];
        uint32_t new_val = shared_state[i];
        if ((current_val | new_val) != current_val) {
            atomicOr(&global_state[i], new_val);
        }
    }

    int block_has_changes = __syncthreads_or(local_changes);
    if (threadIdx.x == 0 && block_has_changes) {
        atomicExch(changes_detected, 1);
    }

    unsigned long long end_time = clock64();
    if (threadIdx.x == 0) {
        atomicAdd(telemetry_cycles, (end_time - start_time));
    }
}

inline int get_val_l4(const std::vector<uint32_t>& state, int var_idx) {
    int int_idx = var_idx / 16;
    int bit_shift = (var_idx % 16) * 2;
    return (state[int_idx] >> bit_shift) & 0b11;
}

inline void set_val_l4(std::vector<uint32_t>& state, int var_idx, int val) {
    int int_idx = var_idx / 16;
    int bit_shift = (var_idx % 16) * 2;
    state[int_idx] &= ~(0b11 << bit_shift); 
    state[int_idx] |= (val << bit_shift);   
}

struct DecimationChoice {
    int var_idx;
    bool guessed_true;
    bool both_tried;
    std::vector<uint32_t> saved_state; 
};

int main(int argc, char** argv) {
    if (argc != 3) {
        printf("Uso: godel_megakernel.exe <payload.bin> <salida.csv>\n");
        return 1;
    }

    std::ifstream file(argv[1], std::ios::binary);
    if (!file) {
        printf("[FATAL] No se pudo abrir payload: %s\n", argv[1]);
        return 1;
    }

    uint32_t num_vars, num_clauses;
    file.read(reinterpret_cast<char*>(&num_vars), sizeof(uint32_t));
    file.read(reinterpret_cast<char*>(&num_clauses), sizeof(uint32_t));
    
    size_t tensor_bytes = (num_vars * 320 * 4) + (num_clauses * 320 * 4);
    file.seekg(8 + tensor_bytes, std::ios::beg);

    std::vector<int> h_clauses(num_clauses * 3);
    file.read(reinterpret_cast<char*>(h_clauses.data()), num_clauses * 3 * sizeof(int));
    file.close();

    int* d_clauses;
    uint32_t* d_state;
    unsigned long long* d_telemetry;
    int* d_changes;
    int state_ints = (num_vars + 15) / 16;
    
    cudaMalloc(&d_clauses, num_clauses * 3 * sizeof(int));
    cudaMalloc(&d_state, state_ints * sizeof(uint32_t));
    cudaMalloc(&d_telemetry, sizeof(unsigned long long));
    cudaMalloc(&d_changes, sizeof(int));

    cudaMemcpy(d_clauses, h_clauses.data(), num_clauses * 3 * sizeof(int), cudaMemcpyHostToDevice);
    cudaMemset(d_state, 0, state_ints * sizeof(uint32_t));
    cudaMemset(d_telemetry, 0, sizeof(unsigned long long));

    int threadsPerBlock = 256;
    int blocksPerGrid = (num_clauses + threadsPerBlock - 1) / threadsPerBlock;
    size_t sharedMemSize = state_ints * sizeof(uint32_t);

    std::ofstream csv_file(argv[2]);
    csv_file << "Iteration,Action,Var_Idx,Value,Vars_N,Vars_B,Depth\n";

    std::vector<uint32_t> h_state(state_ints, 0);
    std::vector<DecimationChoice> stack;
    
    int total_propagations = 0;
    int total_backtracks = 0;
    int max_depth = 0;
    bool is_sat = false;

    auto start_cpu = std::chrono::high_resolution_clock::now();

    while (true) {
        int h_changes = 1;
        while (h_changes > 0) {
            h_changes = 0;
            cudaMemcpy(d_changes, &h_changes, sizeof(int), cudaMemcpyHostToDevice);
            godel_coinductive_kernel<<<blocksPerGrid, threadsPerBlock, sharedMemSize>>>(
                d_clauses, d_state, num_clauses, num_vars, d_telemetry, d_changes
            );
            cudaDeviceSynchronize();
            cudaMemcpy(&h_changes, d_changes, sizeof(int), cudaMemcpyDeviceToHost);
            total_propagations++;
        }

        cudaMemcpy(h_state.data(), d_state, state_ints * sizeof(uint32_t), cudaMemcpyDeviceToHost);
        
        int count_B = 0, count_N = 0;
        int first_N = -1;
        for (int i = 0; i < num_vars; i++) {
            int val = get_val_l4(h_state, i);
            if (val == VAL_B) count_B++;
            else if (val == VAL_N) { count_N++; if (first_N == -1) first_N = i; }
        }

        if (count_B > 0) {
            csv_file << total_propagations << ",OGP_HIT,-1,-1," << count_N << "," << count_B << "," << stack.size() << "\n";
            bool backtrack_successful = false;
            while (!stack.empty()) {
                auto& last_choice = stack.back();
                if (!last_choice.both_tried) {
                    last_choice.both_tried = true;
                    last_choice.guessed_true = !last_choice.guessed_true;
                    h_state = last_choice.saved_state;
                    set_val_l4(h_state, last_choice.var_idx, last_choice.guessed_true ? VAL_T : VAL_F);
                    cudaMemcpy(d_state, h_state.data(), state_ints * sizeof(uint32_t), cudaMemcpyHostToDevice);
                    total_backtracks++;
                    backtrack_successful = true;
                    csv_file << total_propagations << ",BACKTRACK," << last_choice.var_idx << "," 
                             << (last_choice.guessed_true ? "T" : "F") << "," << count_N << "," << count_B << "," << stack.size() << "\n";
                    break;
                } else {
                    stack.pop_back();
                }
            }
            if (!backtrack_successful) break; // UNSAT Absoluto
        } else if (count_N > 0) {
            DecimationChoice c;
            c.var_idx = first_N;
            c.guessed_true = true; 
            c.both_tried = false;
            c.saved_state = h_state; 
            stack.push_back(c);
            if (stack.size() > max_depth) max_depth = stack.size();

            csv_file << total_propagations << ",DECIMATION," << first_N << ",T," << count_N << "," << count_B << "," << stack.size() << "\n";
            set_val_l4(h_state, first_N, VAL_T);
            cudaMemcpy(d_state, h_state.data(), state_ints * sizeof(uint32_t), cudaMemcpyHostToDevice);
        } else {
            is_sat = true;
            break;
        }
    }

    auto end_cpu = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double, std::milli> elapsed_cpu = end_cpu - start_cpu;
    unsigned long long h_telemetry;
    cudaMemcpy(&h_telemetry, d_telemetry, sizeof(unsigned long long), cudaMemcpyDeviceToHost);
    csv_file.close();

    printf("=======================================================================\n");
    printf("  [TELEMETRIA] | CPU Wall-clock: %.3f ms\n", elapsed_cpu.count());
    printf("  [TELEMETRIA] | Ciclos ALU GPU: %llu\n", h_telemetry);
    printf("  [TELEMETRIA] | Propagaciones: %d\n", total_propagations);
    printf("  [TELEMETRIA] | Backtracks (Choques OGP): %d\n", total_backtracks);
    printf("  [TELEMETRIA] | Profundidad Maxima: %d\n", max_depth);
    printf("  [VERDICT]    | %s\n", is_sat ? "SAT (Fase Liquida)" : "UNSAT (Muro Exponencial)");
    printf("=======================================================================\n");

    cudaFree(d_clauses); cudaFree(d_state); cudaFree(d_telemetry); cudaFree(d_changes);
    return 0;
}
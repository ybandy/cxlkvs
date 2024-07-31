import math



class OpTimeModelBase:

    def __init__(self, switch_time, num_prefetches):
        self.switch_time = switch_time
        self.num_prefetches = num_prefetches

    def _combine(self, memory_term, io_term, num_memory_accesses, memory_time, io_time_pre, io_time_post, memory_latency):
        return memory_term + io_term

    def reciprocal_throughput(self, num_memory_accesses, memory_time, io_time_pre, io_time_post, memory_latency):
        memory_term = num_memory_accesses * (memory_time + self.switch_time)
        io_term = io_time_pre + io_time_post + 2 * self.switch_time
        return self._combine(memory_term, io_term, num_memory_accesses, memory_time, io_time_pre, io_time_post, memory_latency)


class OpTimeModelWorst(OpTimeModelBase):

    def __init__(self, switch_time, num_prefetches):
        super().__init__(switch_time, num_prefetches)

    def _combine(self, memory_term, io_term, num_memory_accesses, memory_time, io_time_pre, io_time_post, memory_latency):
        limit = num_memory_accesses * memory_latency / self.num_prefetches
        return max(memory_term, limit) + io_term


class OpTimeModelBest(OpTimeModelBase):

    def __init__(self, switch_time, num_prefetches):
        super().__init__(switch_time, num_prefetches)

    def _combine(self, memory_term, io_term, num_memory_accesses, memory_time, io_time_pre, io_time_post, memory_latency):
        limit = num_memory_accesses * memory_latency / self.num_prefetches
        return max(memory_term + io_term, limit)


class OpTimeModelProbabilistic(OpTimeModelBase):

    def __init__(self, switch_time, num_prefetches):
        super().__init__(switch_time, num_prefetches)

    def _combine(self, memory_term, io_term, num_memory_accesses, memory_time, io_time_pre, io_time_post, memory_latency):
        p_memory = num_memory_accesses / (num_memory_accesses + 2)
        p_io = 1 / (num_memory_accesses + 2)

        expected_wait_time = 0
        expected_seq_length = 0
        wait_time_base = memory_latency - self.num_prefetches * (memory_time + self.switch_time)
        k = 0
        while(True):
            seq_length = self.num_prefetches + k
            rho_k = math.comb(seq_length, k) * math.pow(p_io, k)
            wait_time = wait_time_base - k * (io_time_post + self.switch_time)
            if(rho_k < 1e-6):
                break

            for j in range(self.num_prefetches + 1):
                rho_jk = rho_k * math.comb(self.num_prefetches, j) * math.pow(p_memory, self.num_prefetches - j) * math.pow(p_io, j)
                wait_time -= j * (io_time_pre - memory_time)
                expected_wait_time += rho_jk * max(wait_time, 0)
                expected_seq_length += rho_jk * seq_length
            k += 1
        expected_wait_time *= (num_memory_accesses + 2) / expected_seq_length
        return memory_term + io_term + expected_wait_time

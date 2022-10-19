import os, sys
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

import copy
import numpy as np
import random
from scipy.optimize import linear_sum_assignment

from policy import Policy, PolicyWithPacking

class AlloXPolicy(Policy):
    def __init__(self, alpha=1.0):
        self._name = 'AlloX_Perf'
        self._alpha = alpha
        self._prev_allocation = {}

    def get_allocation(self, unflattened_throughputs,
                       scale_factors, times_since_start,
                       num_steps_remaining,
                       cluster_spec):
        throughputs, index = super().flatten(unflattened_throughputs,
                                             cluster_spec)
        if throughputs is None: return None
        (m, n) = throughputs.shape
        (job_ids, worker_types) = index

        # Make sure all scale factors are 1, since AlloX only supports jobs
        # with scale factors of 1.
        for job_id in scale_factors:
            assert(scale_factors[job_id] == 1)

        # m is the number of jobs, n is the total number of available workers
        # (not the total number of worker types).
        unallocated_job_ids = []
        already_allocated_job_ids = []
        for job_id in unflattened_throughputs:
            if job_id not in self._prev_allocation:
                unallocated_job_ids.append(job_id)
            else:
                total_allocation = 0.0
                for worker_type in worker_types:
                    total_allocation += self._prev_allocation[job_id][worker_type]
                if total_allocation == 1.0:
                    already_allocated_job_ids.append(job_id)
                else:
                    unallocated_job_ids.append(job_id)

        m = len(unallocated_job_ids)
        n = 0
        worker_id_to_worker_type_mapping = {}
        for worker_type in worker_types:
            num_workers = cluster_spec[worker_type]
            for already_allocated_job_id in already_allocated_job_ids:
                if self._prev_allocation[already_allocated_job_id][worker_type] == 1.0:
                    num_workers -= 1
            for worker_id in range(n, n+num_workers):
                worker_id_to_worker_type_mapping[worker_id] = worker_type
                n += 1

        # Sort job IDs according to arrival time.
        unallocated_job_ids.sort(key=lambda x: -times_since_start[x])
        unallocated_job_ids = unallocated_job_ids[:max(int(self._alpha * m), n)] # DEBUG(xlc): 只取一定比例的job处理?
        m = len(unallocated_job_ids)

        # Construct matrix of processing times for each job on each worker,
        # taking into account the type of each worker.
        q_base = np.zeros((m, n)) # DEBUG(xlc): 不同机器上不同任务的剩余执行时间, 这个是个未卜先知的实际值
        for i in range(m):
            for j in range(n):
                worker_type = worker_id_to_worker_type_mapping[j]
                throughput = unflattened_throughputs[unallocated_job_ids[i]][worker_type]
                if throughput == 0.0:
                    throughput = 1e-10
                q_base[i, j] = num_steps_remaining[unallocated_job_ids[i]] / \
                    throughput # DEBUG(xlc): 这一步是正常操作
        # q is computed as [q_base q_base*2 q_base*3 ... q_base*n]. # DEBUG(xlc): 剩余执行时间的[1, 2, ..., n]矩阵
        q = np.copy(q_base)
        for i in range(2, m+1): # DEBUG(xlc): 这一步应该是行数不变, 列数增加, 表示对不同的scale_factor的模拟?
            scaled_q_base = i * q_base
            q = np.concatenate((q, scaled_q_base), axis=1)

        # Construct matrix of delay times for each job on each worker. # DEBUG(xlc): 开始时间的[1, 1, ..., 1]矩阵
        d_base = np.zeros((m, n))
        for i in range(m):
            for j in range(n):
                d_base[i, j] = times_since_start[unallocated_job_ids[i]]
        # d is computed as [d_base d_base d_base ... d_base].
        d = np.copy(d_base)
        for i in range(2, m+1):
            d = np.concatenate((d, d_base), axis=1)

        # Add d to q. # DEBUG(xlc): 这里是对全执行时间做优化 (剩余时间 + 开始时间)
        q = q + d

        # Solve assignment problem using Hungarian method (implemented in scipy).
        row_indices, col_indices = linear_sum_assignment(q) # DEBUG(xlc): 使用匈牙利算法求解最佳匹配问题

        # Extract assignment of jobs to worker types.
        per_worker_id_job_assignment = {i: [] for i in range(n)}
        for (row_index, col_index) in zip(row_indices, col_indices):
            job_id = unallocated_job_ids[row_index]
            worker_id = col_index % n # DEBUG(xlc): 因为输出的矩阵本身就做了扩充, 因此需要求余数得到正确的worker_id
            worker_type = worker_id_to_worker_type_mapping[worker_id]
            worker_type_order = col_index // n
            per_worker_id_job_assignment[worker_id].append((job_id, worker_type_order))
        for worker_id in range(n):
            per_worker_id_job_assignment[worker_id] = [
                (x[0], len(per_worker_id_job_assignment[worker_id]) -1 - x[1])
                for x in per_worker_id_job_assignment[worker_id]] # DEBUG(xlc): 如果没有通过匈牙利算法得到的结果是不会参与这里的计算, 只是做了差值计算
            per_worker_id_job_assignment[worker_id].sort(key=lambda x: x[1])

        # Construct allocation. Don't remember allocations beyond the first
        # for each worker, since these can be recomputed the next time the
        # policy is run. Copy over allocations from already running jobs whose
        # allocations have already been computed.
        allocation = {}
        for job_id in job_ids:
            allocation[job_id] = \
                {worker_type: 0.0 for worker_type in cluster_spec}
        for job_id in job_ids:
            if job_id in self._prev_allocation:
                allocation[job_id] = copy.copy(self._prev_allocation[job_id])
        for worker_id in range(n):
            if len(per_worker_id_job_assignment[worker_id]) > 0:
                job_id = per_worker_id_job_assignment[worker_id][0][0]
                worker_type = worker_id_to_worker_type_mapping[worker_id]
                allocation[job_id][worker_type] = 1.0
        total_workers_allocated = 0
        for job_id in job_ids:
            for worker_type in worker_types:
                total_workers_allocated += allocation[job_id][worker_type]
        self._prev_allocation = copy.copy(allocation)

        return allocation

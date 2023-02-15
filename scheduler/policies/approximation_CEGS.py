import os, sys

sys.path.append(os.path.dirname(os.path.realpath(__file__)))

import copy
import random
import numpy as np

import job_id_pair

from policy import Policy, PolicyWithPacking

class ApproximationCEGSPolicyWithPref(Policy):
    def __init__(self):
        super().__init__()
        self._name = "ApproximationCEGS_Pref"
        self._enable_memory = True
        self._indivial_resource_placement = True
        self._invalid_allocation_zero = True
        self._num_steps_remaining = None

    def valid_mem_request_for_job(self, job_request_mem_per_resource, scale_factor,
                                current_workers_mem_per_type):
        valid_count = sum(mem_per_worker >= job_request_mem_per_resource for mem_per_worker in current_workers_mem_per_type)
        return valid_count >= scale_factor

    def filter_valid_through(self, unflattened_throughputs, current_jobs, scale_factors,
                            current_workers_mem, current_worker_id_to_worker_type):
        result_throughputs = {}
        
        current_workers_mem_per_type = {}
        for worker_id in current_workers_mem:
            work_mem = current_workers_mem[worker_id]
            worker_type = current_worker_id_to_worker_type[worker_id]
            if worker_type not in current_workers_mem_per_type:
                current_workers_mem_per_type[worker_type] = [work_mem]
            else:
                current_workers_mem_per_type[worker_type].append(work_mem)
        
        for job_id in unflattened_throughputs:
            result_throughputs[job_id] = {}
            scale_factor = scale_factors[job_id]
            for worker_type in unflattened_throughputs[job_id]:
                job_request_mem = 0.0
                for single_job_id in job_id.singletons():
                    job_request_mem += current_jobs[single_job_id].memory_request
                job_request_mem_per_resource = job_request_mem / scale_factor
                
                if self.valid_mem_request_for_job(job_request_mem_per_resource, scale_factor, current_workers_mem_per_type[worker_type]):
                    result_throughputs[job_id][worker_type] = unflattened_throughputs[job_id][worker_type]
                else:
                    result_throughputs[job_id][worker_type] = 0.0

        return result_throughputs

    def get_allocation(self, unflattened_throughputs, scale_factors, num_steps_remaining, cluster_spec,
                        current_jobs, current_workers_mem, current_worker_id_to_worker_type, current_prices):
        # DEBUG(xlc): 在throughputs {job_id: {worker_type: []}}中排序
        # DEBUG(xlc): 标准1: 任务的剩余时间
        # DEBUG(xlc): 标准2: 资源的利用情况, 优先分配给已经利用的机器, 建议设置一个标识上轮使用resource字段
        
        # DEBUG(xlc): 直接优先处理无法解决的情况
        available_workers = copy.deepcopy(cluster_spec)
        filter_valid_unflattened_throughputs = self.filter_valid_through(unflattened_throughputs,
                                                                        current_jobs,
                                                                        scale_factors,
                                                                        current_workers_mem, 
                                                                        current_worker_id_to_worker_type)
        throughputs, index = super().flatten(filter_valid_unflattened_throughputs,
                                             cluster_spec)
        if index is None: return None
        (m, n) = throughputs.shape # DEBUG(xlc): (job, machine)
        (job_ids, worker_types) = index
        self._num_steps_remaining = np.array([num_steps_remaining[job_id]
                                              for job_id in job_ids])
        if throughputs is None: return None
        # scale_factors_array = self.scale_factors_array(
        #      scale_factors, job_ids, m, n) # DEBUG(xlc): (job, machine)

        time_remain_matrix = self._num_steps_remaining[:, np.newaxis] / throughputs
        max_time_remain_sort_indexes = np.max(time_remain_matrix, axis=1).argsort()
        sort_throughputs = throughputs[max_time_remain_sort_indexes]

        current_prices_array = np.ones((n, ))
        for i in range(n):
            current_prices_array[i] = current_prices[worker_types[i]]
        price_remain_matrix = np.multiply(self._num_steps_remaining[:, np.newaxis] / sort_throughputs, current_prices_array)
        min_time_remain_sort_indexes = np.argmin(price_remain_matrix, axis=1)

        result_queue = []
        for row_index in range(m):
            # job_id = job_ids[max_time_remain_sort_indexes[row_index]]
            # resource_type = worker_types[min_time_remain_sort_indexes[row_index]]
            result_queue.append((max_time_remain_sort_indexes[row_index], min_time_remain_sort_indexes[row_index]))

        # Find all available workers.
        available_worker_types = []
        for worker_type in available_workers:
            if available_workers[worker_type] > 0:
                available_worker_types.append(worker_type)
        available_worker_types.sort()

        real_allocation = {}
        while len(result_queue) > 0 and len(available_worker_types) > 0:
            (job_index, worker_index) = result_queue.pop(0)
            job_id_to_schedule = job_ids[job_index]
            worker_type = worker_types[worker_index]
            scale_factor = scale_factors[job_id_to_schedule]
            # 按queue顺序决定调度即可
            if available_workers[worker_type] < available_workers[worker_type]:
                continue
            if throughputs[job_index][worker_index] > 0.0:
                real_allocation[job_id_to_schedule] = worker_type
                available_workers[worker_type] -= scale_factor
                if available_workers[worker_type] == 0:
                    available_worker_types.pop(available_worker_types.index(worker_type))
            
        
        final_allocation = {}
        for job_id in unflattened_throughputs:
            final_allocation[job_id] = \
                {worker_type: 0.0 for worker_type in cluster_spec}
        for job_id, worker_type in real_allocation.items():
            final_allocation[job_id][worker_type] = 1.0
        return final_allocation

    def do_resource_placement_policy(self, scheduled_jobs, current_scale_factor, 
                                    all_worker_ids, worker_last_rent_status, assigned_worker_ids, 
                                    new_worker_assignments):
        result_assignments_worker = {}
        for (job_id, scale_factor) in scheduled_jobs:
            if scale_factor != current_scale_factor: # DEBUG(xlc): 因为存在两个一模一样的排序, 所以可以保证这一步必然不成立
                continue
            valid_worker_ids = [(all_worker_ids[ptr][0], ptr) for ptr in range(len(all_worker_ids)) if (
                len(all_worker_ids[ptr]) > 0 and 
                all_worker_ids[ptr][0] in worker_last_rent_status and 
                all_worker_ids[ptr][0] not in assigned_worker_ids and 
                worker_last_rent_status[all_worker_ids[ptr][0]] == True
            )]
            if job_id not in new_worker_assignments:
                result_assignments_worker[job_id] = []
            else:
                result_assignments_worker[job_id] = list(new_worker_assignments[job_id])
            while (len(result_assignments_worker[job_id]) < scale_factor) \
                and len(valid_worker_ids) > 0:
                (worker_id_to_assign, _) = valid_worker_ids.pop(0)
                result_assignments_worker[job_id].append(worker_id_to_assign)
                assigned_worker_ids.add(worker_id_to_assign)
            if len(result_assignments_worker[job_id]) > 0:
                new_worker_assignments[job_id] = tuple(result_assignments_worker[job_id])

class ApproximationCEGSPolicyWithPacking(PolicyWithPacking):
    def __init__(self):
        super().__init__()
        self._name = "ApproximationCEGS_Packing"
        self._enable_memory = True
        self._allocation = {}
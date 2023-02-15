import os, sys

sys.path.append(os.path.dirname(os.path.realpath(__file__)))

import copy
import random
import numpy as np


import job_id_pair

from policy import Policy, PolicyWithPacking

class PrivacyBudgetClientPolicyWithPref(Policy):
    def __init__(self):
        super().__init__()
        self._name = "PrivacyBudgetClientPref"
        self._enable_data = True
        self._invalid_allocation_zero = True

    def _get_allocation(self, throughputs, index, scale_factors_array,
                        cluster_spec):
        (_, worker_types) = index
        (m, n) = throughputs.shape

        # Split cluster over users (m). By construction,
        # \sum_i (x[i, j] * scale_factor[i]) = num_workers[j].
        # Normalize to ensure \sum_j x[i, j] <= 1 for all i.
        x = np.array([[cluster_spec[worker_type] / m for worker_type in worker_types]
                      for i in range(m)])
        x = x / scale_factors_array
        per_row_sum = np.sum(x, axis=1)
        per_row_sum = np.maximum(per_row_sum, np.ones(per_row_sum.shape))
        x = x / per_row_sum[:, None]

        return x

    def get_allocation(self, unflattened_throughputs, scale_factors,
                        cluster_spec, target_datablock_id):
        # feature(xlc): 首先过滤掉不进行调度的数据块
        job_unallocate_datablock_id_state = {key: value for key, value in target_datablock_id.items() if value == -1}
        new_unflattened_throughputs = {}
        failed_scheduled_job_ids = []
        for job_id in unflattened_throughputs:
            valid_in_new_throughput = True
            for single_job_id in job_id.singletons():
                if single_job_id in job_unallocate_datablock_id_state:
                    valid_in_new_throughput = False
            if valid_in_new_throughput:
                new_unflattened_throughputs[job_id] = unflattened_throughputs[job_id]
            else:
                failed_scheduled_job_ids.append(job_id)
        # print(new_unflattened_throughputs)
        throughputs, index = super().flatten(new_unflattened_throughputs,
                                             cluster_spec)
        if throughputs is None: return None
        (job_ids, worker_types) = index
        (m, n) = throughputs.shape

        scale_factors_array = self.scale_factors_array(
            scale_factors, job_ids, m, n)

        x = self._get_allocation(throughputs, index,
                                 scale_factors_array,
                                 cluster_spec)
        valid_result = super().unflatten(x, index)        
        for failed_job in failed_scheduled_job_ids:
            for worker_type in worker_types:
                valid_result[failed_job][worker_type] = 0.0
        return valid_result

    def get_privacy_client_allocation(self, datablock_state, significant_matrix):
        # print("get_privacy_client_allocation: Nothing Happen!")
        # feature(xlc): 对仍然没有分配datablock的job进行分配
        # print("check datablock_state: {}".format(datablock_state))
        job_unallocate_datablock_id_state = {key: value for key, value in datablock_state['job_allocate_datablock_id'].items() if value == -1}
        result_update_datablock_state = {}
        temp_privacy_budget_remain_state = copy.deepcopy(datablock_state['datablock_privacy_budget_remain'])
        for job_id in job_unallocate_datablock_id_state:
            # 获得目的dataset
            target_dataset = datablock_state['job_target_dataset'][job_id]
            job_privacy_budget_consume = datablock_state['job_privacy_budget_consume'][job_id]
            origin_datablocks_in_dataset = datablock_state['dataset_type_to_datablock_id_mapping'][target_dataset]
            valid_datablocks = [datablock for datablock in origin_datablocks_in_dataset 
                                if temp_privacy_budget_remain_state[datablock] >= job_privacy_budget_consume]
            random_result_id = random.choice(range(len(valid_datablocks))) # feature(xlc): 随机取一个valid datablock分配即可
            random_result_db = valid_datablocks[random_result_id]
            temp_privacy_budget_remain_state[random_result_db] -= job_privacy_budget_consume
            result_update_datablock_state[job_id] = random_result_db
        return result_update_datablock_state
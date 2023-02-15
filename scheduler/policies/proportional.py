import os, sys
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

import numpy as np

from policy import Policy

class ProportionalPolicy(Policy):

    def __init__(self):
        super().__init__()
        self._name = 'Proportional'

    def get_throughputs(self, throughputs, index,
                        cluster_spec):
        if throughputs is None: return None
        (job_ids, worker_types) = index
        (m, n) = throughputs.shape

        x_proportional = self._get_allocation(
            throughputs, index,
            cluster_spec)
        proportional_throughputs = np.sum(np.multiply(throughputs, x_proportional), # DEBUG(xlc): (T * x) => 对应元素相乘, 对每一行(每个任务)求和
                                          axis=1).reshape((m, 1))
        return proportional_throughputs

    def _get_allocation(self, throughputs, index,
                        cluster_spec):
        (_, worker_types) = index
        (m, n) = throughputs.shape

        # Split cluster over users (m).
        # x[i, j] proportional to num_workers[j].
        # \sum_j x[i, j] <= 1 for all i.
        # \sum_i x[i, j] <= 1 for all j.
        x = np.array([[cluster_spec[worker_type] / m for worker_type in worker_types]
                      for i in range(m)]) # DEBUG(xlc): 每个任务平均分配当前可用的节点
        max_per_row_sum = np.sum(x, axis=1).max()
        x = x / max_per_row_sum # DEBUG(xlc): 归一化, 对目前所有可用的cluster_spec, 计算归一化的X

        return x

    def get_allocation(self, unflattened_throughputs,
                       cluster_spec):
        throughputs, index = super().flatten(unflattened_throughputs,
                                             cluster_spec)
        if throughputs is None: return None
        (job_ids, worker_types) = index
        (m, n) = throughputs.shape

        x = self._get_allocation(throughputs, index,
                                 cluster_spec)

        return super().unflatten(x, index)

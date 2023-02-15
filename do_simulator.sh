# python /home/ubuntu/data/labInDiWu/gavel/scheduler/scripts/sweeps/run_sweep_continuous.py \
#         --window-start 0 \
#         --window-end 100 \
#         --log-dir /home/ubuntu/data/labInDiWu/gavel/logs \
#         --processes 4 \
#         --policies approximation_CEGS_perf \
#         --seeds 0 \
#         --cluster-spec 36:36:36 \
#         --generate-multi-gpu-jobs \
#         --verbose \
#         --per_instance_type_prices_dir /home/ubuntu/data/labInDiWu/gavel/type_prices \
#         --available_clouds aws gcp \
#         --throughput-lower-bound 0.0 \
#         --throughput-upper-bound 1.0 \
#         --num-data-points 5 \
#         --mem_enable

python /home/ubuntu/data/labInDiWu/gavel/scheduler/scripts/sweeps/run_sweep_continuous.py \
        --window-start 0 \
        --window-end 5 \
        --log-dir /home/ubuntu/data/labInDiWu/gavel/logs \
        --processes 1 \
        --policies privacy_budget_client_perf \
        --seeds 0 \
        --cluster-spec 16:16:16 \
        --generate-multi-gpu-jobs \
        --verbose \
        --per_instance_type_prices_dir /home/ubuntu/data/labInDiWu/gavel/type_prices \
        --available_clouds aws gcp \
        --throughput-lower-bound 0.0 \
        --throughput-upper-bound 1.0 \
        --num-data-points 2 \
        --data_enable

# python /home/ubuntu/data/labInDiWu/gavel/scheduler/scripts/sweeps/run_sweep_continuous.py \
#         --window-start 0 \
#         --window-end 100 \
#         --log-dir /home/ubuntu/data/labInDiWu/gavel/logs \
#         --processes 4 \
#         --policies fifo_perf isolated max_min_fairness_perf max_sum_throughput_perf max_sum_throughput_normalized_by_cost_perf \
#         min_total_duration_perf max_min_fairness_water_filling_perf \
#         --seeds 0 \
#         --cluster-spec 12:12:12 \
#         --generate-multi-gpu-jobs \
#         --verbose \
#         --per_instance_type_prices_dir /home/ubuntu/data/labInDiWu/gavel/type_prices \
#         --available_clouds aws gcp \
#         --throughput-lower-bound 0.0 \
#         --throughput-upper-bound 1.0 \
#         --num-data-points 5 \


# python scheduler/scripts/drivers/simulate_scheduler_with_generated_jobs.py \
#         --window-start 0 \
#         --window-end 100 \
#         --policy fifo_perf isolated max_min_fairness_perf max_sum_throughput_perf max_sum_throughput_normalized_by_cost_perf \
#         min_total_duration_perf max_min_fairness_water_filling_perf approximation_CEGS_perf \
#         --seed 0 \
#         --lam 28800.0 \
#         --cluster_spec 36:36:36 \
#         --generate-multi-gpu-jobs \
#         --generate-multi-priority-jobs \
#         --verbose \
#         --assign_SLOs \
#         --throughputs_file /home/ubuntu/data/labInDiWu/gavel/scheduler/simulation_throughputs.json \
#         --per_instance_type_prices_dir /home/ubuntu/data/labInDiWu/gavel/type_prices \
#         --available_clouds aws gcp
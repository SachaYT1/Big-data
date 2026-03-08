-- Run on coordinator after docker compose up
-- Adds worker nodes to the cluster

SELECT citus_set_coordinator_host('coordinator', 5432);
SELECT citus_add_node('worker1', 5432)
WHERE NOT EXISTS (
    SELECT 1
    FROM pg_dist_node
    WHERE nodename = 'worker1' AND nodeport = 5432
);

SELECT citus_add_node('worker2', 5432)
WHERE NOT EXISTS (
    SELECT 1
    FROM pg_dist_node
    WHERE nodename = 'worker2' AND nodeport = 5432
);

SELECT * FROM citus_get_active_worker_nodes();

from .pods import pods, logs, exec, pods_by_node, describe, delete
from .metrics import pod_metrics, all_metrics
from .config import init, use, login_aws, use_cluster, clusters, login_azure, init_azure
from .nodes import nodes, describe_node, node_metrics
from .namespaces import namespaces
from .ingress import urls, loadbalancer
from .storage import pvs, pvcs, storage

__all__ = [
    'pods',
    'logs',
    'exec',
    'pods_by_node',
    'describe',
    'delete',
    'pod_metrics',
    'all_metrics',
    'init',
    'use',
    'login_aws',
    'use_cluster',
    'clusters',
    'nodes',
    'describe_node',
    'namespaces',
    'urls',
    'loadbalancer',
    'pvs',
    'pvcs',
    'storage',
    'node_metrics',
    'login_azure',
    'init_azure'
] 
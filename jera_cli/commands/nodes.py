import click
from rich.console import Console
from rich.table import Table
from kubernetes import client, config
from ..utils.kubernetes import format_age, get_pod_metrics, parse_resource_value

console = Console()

@click.command()
def nodes():
    """Lista todos os nós do cluster com informações detalhadas."""
    try:
        config.load_kube_config()
        v1 = client.CoreV1Api()
        
        console.print("\n🔄 Obtendo informações dos nós...", style="yellow")
        
        nodes = v1.list_node()
        
        table = Table(title="📊 Nós do Cluster", show_header=True)
        table.add_column("Nome", style="cyan")
        table.add_column("Status", justify="center")
        table.add_column("Roles", style="blue")
        table.add_column("Versão", style="magenta")
        table.add_column("CPU", justify="right")
        table.add_column("Memória", justify="right")
        table.add_column("Idade", justify="right")
        
        for node in nodes.items:
            # Nome do nó
            name = node.metadata.name
            
            # Status
            status = "Ready"
            status_style = "green"
            for condition in node.status.conditions:
                if condition.type == "Ready":
                    if condition.status != "True":
                        status = "NotReady"
                        status_style = "red"
                    break
            
            # Roles
            roles = []
            for label, value in node.metadata.labels.items():
                if label.startswith("node-role.kubernetes.io/"):
                    role = label.split("/")[1]
                    roles.append(role)
            roles = ", ".join(roles) if roles else "worker"
            
            # Versão do Kubernetes
            version = node.status.node_info.kubelet_version
            
            # Recursos
            allocatable_cpu = node.status.allocatable.get('cpu', '0')
            allocatable_memory = node.status.allocatable.get('memory', '0')
            
            # Converte memória para GB
            memory_bytes = parse_resource_value(allocatable_memory, 'memory')
            memory_gb = round(memory_bytes / 1024, 1)  # Converte Mi para Gi
            
            # Idade
            age = format_age(node.metadata.creation_timestamp)
            
            table.add_row(
                name,
                f"[{status_style}]{status}[/{status_style}]",
                roles,
                version,
                f"{allocatable_cpu} cores",
                f"{memory_gb}Gi",
                age
            )
        
        console.print()
        console.print(table)
        console.print()
        
    except Exception as e:
        console.print(f"❌ Erro ao listar nós: {str(e)}", style="bold red") 
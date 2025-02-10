import click
from rich.console import Console
from rich.table import Table
from kubernetes import client, config
from ..utils.kubernetes import format_age, get_pod_metrics, parse_resource_value
import inquirer

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

@click.command()
@click.argument('node_name', required=False)
def describe(node_name=None):
    """Mostra informações detalhadas de um nó."""
    try:
        config.load_kube_config()
        v1 = client.CoreV1Api()
        
        # Lista todos os nós
        nodes = v1.list_node()
        node_names = [node.metadata.name for node in nodes.items]
        
        if not node_names:
            console.print("❌ Nenhum nó encontrado no cluster.", style="bold red")
            return
        
        selected_node = node_name
        
        # Se não foi fornecido um nó, mostra a lista interativa
        if not selected_node:
            questions = [
                inquirer.List('node',
                             message="Selecione um nó para ver detalhes",
                             choices=node_names,
                             )
            ]
            answers = inquirer.prompt(questions)
            
            if answers:
                selected_node = answers['node']
            else:
                return
        
        # Verifica se o nó existe
        if selected_node not in node_names:
            console.print(f"❌ Nó '{selected_node}' não encontrado.", style="bold red")
            return
        
        # Obtém os detalhes do nó
        node = next(node for node in nodes.items if node.metadata.name == selected_node)
        
        # Cria a tabela de informações gerais
        table = Table(title=f"📊 Detalhes do Nó: [bold cyan]{selected_node}[/]", show_header=True)
        table.add_column("Campo", style="blue")
        table.add_column("Valor")
        
        # Informações básicas
        table.add_row("Nome", node.metadata.name)
        table.add_row("UID", str(node.metadata.uid))
        table.add_row("Criado em", format_age(node.metadata.creation_timestamp))
        
        # Roles
        roles = []
        for label, value in node.metadata.labels.items():
            if label.startswith("node-role.kubernetes.io/"):
                role = label.split("/")[1]
                roles.append(role)
        table.add_row("Roles", ", ".join(roles) if roles else "worker")
        
        # Informações do sistema
        table.add_row("Arquitetura", node.status.node_info.architecture)
        table.add_row("Container Runtime", node.status.node_info.container_runtime_version)
        table.add_row("Kernel Version", node.status.node_info.kernel_version)
        table.add_row("OS Image", node.status.node_info.os_image)
        table.add_row("Kubelet Version", node.status.node_info.kubelet_version)
        
        # Status
        status = "Ready"
        status_style = "green"
        for condition in node.status.conditions:
            if condition.type == "Ready":
                if condition.status != "True":
                    status = "NotReady"
                    status_style = "red"
                break
        table.add_row("Status", f"[{status_style}]{status}[/{status_style}]")
        
        # Recursos
        allocatable_cpu = node.status.allocatable.get('cpu', '0')
        allocatable_memory = node.status.allocatable.get('memory', '0')
        memory_gb = round(parse_resource_value(allocatable_memory, 'memory') / 1024, 1)
        
        table.add_row("CPU Alocável", f"{allocatable_cpu} cores")
        table.add_row("Memória Alocável", f"{memory_gb}Gi")
        
        console.print()
        console.print(table)
        
        # Tabela de condições
        conditions_table = Table(title="\n🔄 Condições", show_header=True)
        conditions_table.add_column("Tipo", style="cyan")
        conditions_table.add_column("Status", style="yellow")
        conditions_table.add_column("Última Transição", style="blue")
        conditions_table.add_column("Mensagem")
        
        for condition in node.status.conditions:
            status_style = "green" if condition.status == "True" else "red"
            conditions_table.add_row(
                condition.type,
                f"[{status_style}]{condition.status}[/{status_style}]",
                format_age(condition.last_transition_time),
                condition.message or "N/A"
            )
        
        console.print()
        console.print(conditions_table)
        
        # Eventos relacionados ao nó
        events = v1.list_event_for_all_namespaces(
            field_selector=f'involvedObject.name={selected_node},involvedObject.kind=Node'
        )
        
        if events.items:
            events_table = Table(title="\n📝 Eventos Recentes", show_header=True)
            events_table.add_column("Tipo", style="cyan")
            events_table.add_column("Razão", style="yellow")
            events_table.add_column("Idade", style="blue")
            events_table.add_column("Mensagem")
            
            for event in events.items:
                events_table.add_row(
                    event.type,
                    event.reason,
                    format_age(event.first_timestamp),
                    event.message
                )
            
            console.print()
            console.print(events_table)
        
        console.print()
        
    except Exception as e:
        console.print(f"❌ Erro ao descrever nó: {str(e)}", style="bold red") 
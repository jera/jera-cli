import click
from rich.console import Console
from rich.table import Table
from rich.live import Live
import inquirer
import yaml
import os
from kubernetes import client, config
from ..utils.kubernetes import format_age, get_pod_metrics, parse_resource_value
import subprocess
import time

console = Console()

def load_namespace():
    """Carrega o namespace salvo na configuração"""
    config_path = os.path.expanduser('~/.jera/config')
    if os.path.exists(config_path):
        with open(config_path) as f:
            config_data = yaml.safe_load(f)
            return config_data.get('namespace')
    return None

def generate_pods_table(v1, namespace):
    """Gera a tabela de pods para exibição"""
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Nome do Pod")
    table.add_column("Ready", justify="center")
    table.add_column("Status")
    table.add_column("IP")
    table.add_column("Idade")
    
    pods = v1.list_namespaced_pod(namespace)
    
    for pod in pods.items:
        age_str = format_age(pod.metadata.creation_timestamp)
        
        # Calcula o status de Ready
        ready_count = 0
        container_count = len(pod.spec.containers)
        for container_status in pod.status.container_statuses if pod.status.container_statuses else []:
            if container_status.ready:
                ready_count += 1
        ready_status = f"{ready_count}/{container_count}"
        
        # Define o estilo baseado no status
        ready_style = "green" if ready_count == container_count else "red"
        
        table.add_row(
            pod.metadata.name,
            f"[{ready_style}]{ready_status}[/{ready_style}]",
            pod.status.phase,
            pod.status.pod_ip or "N/A",
            age_str
        )
    
    return table

@click.command()
@click.option('-w', '--watch', is_flag=True, help='Atualiza a lista de pods em tempo real')
def pods(watch):
    """Lista todos os pods no namespace atual."""
    try:
        namespace = load_namespace()
        if not namespace:
            console.print("❌ Namespace não definido. Use 'jeracli use <namespace>' primeiro.", style="bold red")
            return

        config.load_kube_config()
        v1 = client.CoreV1Api()
        
        if watch:
            console.print(f"\n🔄 Monitorando pods no namespace [bold green]{namespace}[/]...", style="yellow")
            console.print("Pressione Ctrl+C para parar\n", style="dim")
            
            with Live(generate_pods_table(v1, namespace), refresh_per_second=1) as live:
                try:
                    while True:
                        live.update(generate_pods_table(v1, namespace))
                        time.sleep(1)
                except KeyboardInterrupt:
                    console.print("\n✅ Monitoramento finalizado!", style="bold green")
        else:
            console.print(generate_pods_table(v1, namespace))
            
    except Exception as e:
        console.print(f"❌ Erro ao listar pods: {str(e)}", style="bold red")

@click.command()
@click.argument('pod_name', required=False)
@click.option('-f', '--follow', is_flag=True, help='Acompanha os logs em tempo real')
@click.option('-n', '--tail', type=int, default=None, help='Número de linhas para mostrar (do final)')
def logs(pod_name=None, follow=False, tail=None):
    """Visualiza logs de um pod no namespace atual."""
    try:
        namespace = load_namespace()
        if not namespace:
            console.print("❌ Namespace não definido. Use 'jeracli use <namespace>' primeiro.", style="bold red")
            return

        result = subprocess.run(
            ["kubectl", "get", "pods", "-n", namespace, "-o", "name"],
            capture_output=True,
            text=True,
            check=True
        )
        
        pod_names = [pod.replace('pod/', '') for pod in result.stdout.strip().split('\n') if pod]
        
        if not pod_names:
            console.print("❌ Nenhum pod encontrado no namespace atual.", style="bold red")
            return
        
        selected_pod = pod_name
        
        if not selected_pod:
            questions = [
                inquirer.List('pod',
                             message="Selecione um pod para ver os logs",
                             choices=pod_names,
                             )
            ]
            answers = inquirer.prompt(questions)
            
            if answers:
                selected_pod = answers['pod']
            else:
                return
        
        if selected_pod not in pod_names:
            console.print(f"❌ Pod '{selected_pod}' não encontrado no namespace {namespace}.", style="bold red")
            return
            
        cmd = ["kubectl", "logs", "-n", namespace]
        
        if follow:
            cmd.append("-f")
            
        if tail is not None:
            cmd.extend(["--tail", str(tail)])
            
        cmd.append(selected_pod)
            
        subprocess.run(cmd)
    except Exception as e:
        console.print(f"❌ Erro ao obter logs: {str(e)}", style="bold red")

@click.command()
@click.argument('pod_name', required=False)
def exec(pod_name=None):
    """Executa um shell interativo dentro de um pod."""
    try:
        namespace = load_namespace()
        if not namespace:
            console.print("❌ Namespace não definido. Use 'jeracli use <namespace>' primeiro.", style="bold red")
            return

        result = subprocess.run(
            ["kubectl", "get", "pods", "-n", namespace, "-o", "name"],
            capture_output=True,
            text=True,
            check=True
        )
        
        pod_names = [pod.replace('pod/', '') for pod in result.stdout.strip().split('\n') if pod]
        
        if not pod_names:
            console.print("❌ Nenhum pod encontrado no namespace atual.", style="bold red")
            return
        
        selected_pod = pod_name
        
        if not selected_pod:
            questions = [
                inquirer.List('pod',
                             message="Selecione um pod para conectar",
                             choices=pod_names,
                             )
            ]
            answers = inquirer.prompt(questions)
            
            if answers:
                selected_pod = answers['pod']
            else:
                return
        
        if selected_pod not in pod_names:
            console.print(f"❌ Pod '{selected_pod}' não encontrado no namespace {namespace}.", style="bold red")
            return
            
        console.print(f"\n🔌 Conectando ao pod [bold cyan]{selected_pod}[/] no namespace [bold green]{namespace}[/]...", style="yellow")
        console.print("💡 Use [bold]exit[/] para sair do shell\n", style="dim")
            
        subprocess.run([
            "kubectl", "exec",
            "-it", selected_pod,
            "-n", namespace,
            "--", "/bin/sh"
        ])
    except Exception as e:
        console.print(f"❌ Erro ao executar shell no pod: {str(e)}", style="bold red")

@click.command(name="pods-by-node")
@click.argument('namespace', required=False)
def pods_by_node(namespace=None):
    """Lista todos os pods agrupados por nó, opcionalmente filtrados por namespace."""
    try:
        config.load_kube_config()
        v1 = client.CoreV1Api()
        
        # Se nenhum namespace for especificado, busca todos os namespaces
        if not namespace:
            console.print("\n🔄 Listando pods em todos os namespaces por nó...", style="yellow")
            pods = v1.list_pod_for_all_namespaces()
        else:
            console.print(f"\n🔄 Listando pods no namespace [bold green]{namespace}[/] por nó...", style="yellow")
            pods = v1.list_namespaced_pod(namespace)
        
        # Agrupa pods por nó
        nodes_pods = {}
        for pod in pods.items:
            node_name = pod.spec.node_name or "Não atribuído"
            pod_namespace = pod.metadata.namespace
            
            # Calcula o tempo de vida do pod
            start_time = pod.status.start_time
            if start_time:
                lifetime = format_age(start_time)
            else:
                lifetime = "N/A"
            
            if node_name not in nodes_pods:
                nodes_pods[node_name] = []
            
            nodes_pods[node_name].append({
                'name': pod.metadata.name,
                'namespace': pod_namespace,
                'status': pod.status.phase,
                'ready': f"{sum(1 for status in pod.status.container_statuses if status.ready)}/{len(pod.spec.containers)}" if pod.status.container_statuses else "0/0",
                'lifetime': lifetime
            })
        
        # Cria a tabela
        for node, node_pods in nodes_pods.items():
            table = Table(title=f"📦 Pods no Nó: [bold cyan]{node}[/]", show_header=True)
            table.add_column("Namespace", style="blue")
            table.add_column("Nome do Pod", style="magenta")
            table.add_column("Status", style="blue")
            table.add_column("Ready", justify="center")
            table.add_column("Tempo de Vida", justify="right", style="green")
            
            for pod in node_pods:
                # Define o estilo do status
                status_style = "green" if pod['status'] == "Running" else "yellow"
                
                # Define o estilo do ready
                ready_parts = pod['ready'].split('/')
                ready_style = "green" if ready_parts[0] == ready_parts[1] and ready_parts[1] != "0" else "red"
                
                table.add_row(
                    pod['namespace'],
                    pod['name'],
                    f"[{status_style}]{pod['status']}[/{status_style}]",
                    f"[{ready_style}]{pod['ready']}[/{ready_style}]",
                    pod['lifetime']
                )
            
            console.print()
            console.print(table)
        
        # Resumo
        console.print("\n📊 Resumo:", style="bold")
        console.print(f"Total de Nós: [bold green]{len(nodes_pods)}[/]")
        console.print(f"Total de Pods: [bold green]{sum(len(pods) for pods in nodes_pods.values())}[/]")
        
    except Exception as e:
        console.print(f"❌ Erro ao listar pods por nó: {str(e)}", style="bold red") 
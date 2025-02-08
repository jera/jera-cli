import click
from rich.console import Console
from rich.table import Table
import inquirer
import yaml
import os
from kubernetes import client, config
from ..utils.kubernetes import format_age, get_pod_metrics, parse_resource_value
import subprocess

console = Console()

def load_namespace():
    """Carrega o namespace salvo na configuração"""
    config_path = os.path.expanduser('~/.jera/config')
    if os.path.exists(config_path):
        with open(config_path) as f:
            config_data = yaml.safe_load(f)
            return config_data.get('namespace')
    return None

@click.command()
def pods():
    """Lista todos os pods no namespace atual."""
    try:
        namespace = load_namespace()
        if not namespace:
            console.print("❌ Namespace não definido. Use 'jeracli use <namespace>' primeiro.", style="bold red")
            return

        config.load_kube_config()
        v1 = client.CoreV1Api()
        
        pods = v1.list_namespaced_pod(namespace)
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Nome do Pod")
        table.add_column("Status")
        table.add_column("IP")
        table.add_column("Idade")
        
        for pod in pods.items:
            age_str = format_age(pod.metadata.creation_timestamp)
            
            table.add_row(
                pod.metadata.name,
                pod.status.phase,
                pod.status.pod_ip or "N/A",
                age_str
            )
        
        console.print(table)
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
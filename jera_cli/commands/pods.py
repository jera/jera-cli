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

@click.command()
@click.argument('pod_name', required=False)
def describe(pod_name=None):
    """Mostra informações detalhadas de um pod.
    
    Se o nome do pod não for fornecido, apresenta uma lista interativa
    de pods disponíveis. Mostra informações detalhadas como:
    - Labels e anotações
    - Status detalhado
    - Eventos recentes
    - Volumes montados
    - Condições atuais
    - Informações do container
    
    Requer que um namespace tenha sido selecionado usando 'jeracli use'.
    
    Exemplos:
        $ jeracli describe              # Seleciona pod interativamente
        $ jeracli describe meu-pod      # Mostra detalhes do pod especificado
    """
    try:
        # Load saved namespace
        config_path = os.path.expanduser('~/.jera/config')
        if os.path.exists(config_path):
            with open(config_path) as f:
                config_data = yaml.safe_load(f)
                namespace = config_data.get('namespace')
        
        if not namespace:
            console.print("❌ Namespace não definido. Use 'jeracli use <namespace>' primeiro.", style="bold red")
            return

        # Get list of pods using kubectl
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
        
        # Se não foi fornecido um nome de pod, mostra a lista interativa
        if not selected_pod:
            questions = [
                inquirer.List('pod',
                             message="Selecione um pod para ver os detalhes",
                             choices=pod_names,
                             )
            ]
            answers = inquirer.prompt(questions)
            
            if answers:
                selected_pod = answers['pod']
            else:
                return
        
        # Verifica se o pod existe
        if selected_pod not in pod_names:
            console.print(f"❌ Pod '{selected_pod}' não encontrado no namespace {namespace}.", style="bold red")
            return
            
        # Obtém os detalhes do pod
        config.load_kube_config()
        v1 = client.CoreV1Api()
        pod = v1.read_namespaced_pod(selected_pod, namespace)
        
        # Cria tabelas para diferentes seções de informação
        console.print(f"\n🔍 Detalhes do Pod [bold cyan]{selected_pod}[/] no namespace [bold green]{namespace}[/]", style="bold")
        
        # Informações Básicas
        basic_table = Table(show_header=True, header_style="bold magenta", title="📋 Informações Básicas")
        basic_table.add_column("Campo", style="cyan")
        basic_table.add_column("Valor", style="yellow")
        
        basic_table.add_row("Nome", pod.metadata.name)
        basic_table.add_row("Namespace", pod.metadata.namespace)
        basic_table.add_row("Node", pod.spec.node_name or "N/A")
        basic_table.add_row("IP do Pod", pod.status.pod_ip or "N/A")
        basic_table.add_row("IP do Host", pod.status.host_ip or "N/A")
        basic_table.add_row("QoS Class", pod.status.qos_class or "N/A")
        
        # Calcula a idade
        creation_time = pod.metadata.creation_timestamp
        age = time.time() - creation_time.timestamp()
        if age < 60:  # menos de 1 minuto
            age_str = f"{int(age)}s"
        elif age < 3600:  # menos de 1 hora
            age_str = f"{int(age/60)}m"
        elif age < 86400:  # menos de 1 dia
            age_str = f"{int(age/3600)}h"
        else:
            age_str = f"{int(age/86400)}d"
        basic_table.add_row("Idade", age_str)
        
        console.print()
        console.print(basic_table)
        
        # Labels
        if pod.metadata.labels:
            console.print("\n🏷️  [bold]Labels:[/]")
            for key, value in pod.metadata.labels.items():
                console.print(f"  • {key}: [yellow]{value}[/]")
        
        # Status e Condições
        status_table = Table(show_header=True, header_style="bold magenta", title="\n📊 Status e Condições")
        status_table.add_column("Tipo", style="cyan")
        status_table.add_column("Status", style="yellow")
        status_table.add_column("Última Transição", style="green")
        
        for condition in pod.status.conditions:
            # Calcula o tempo desde a última transição
            last_transition = condition.last_transition_time
            if last_transition:
                transition_age = time.time() - last_transition.timestamp()
                if transition_age < 60:
                    transition_str = f"{int(transition_age)}s"
                elif transition_age < 3600:
                    transition_str = f"{int(transition_age/60)}m"
                elif transition_age < 86400:
                    transition_str = f"{int(transition_age/3600)}h"
                else:
                    transition_str = f"{int(transition_age/86400)}d"
            else:
                transition_str = "N/A"
            
            status_table.add_row(
                condition.type,
                "✅" if condition.status == "True" else "❌",
                transition_str
            )
        
        console.print()
        console.print(status_table)
        
        # Containers
        for container in pod.spec.containers:
            container_table = Table(
                show_header=True,
                header_style="bold magenta",
                title=f"\n📦 Container: [bold cyan]{container.name}[/]"
            )
            container_table.add_column("Campo", style="cyan")
            container_table.add_column("Valor", style="yellow")
            
            container_table.add_row("Image", container.image)
            
            # Recursos
            if container.resources:
                if container.resources.requests:
                    for resource, value in container.resources.requests.items():
                        container_table.add_row(f"Requests {resource}", str(value))
                if container.resources.limits:
                    for resource, value in container.resources.limits.items():
                        container_table.add_row(f"Limits {resource}", str(value))
            
            # Status do container
            container_status = next(
                (status for status in pod.status.container_statuses
                 if status.name == container.name),
                None
            )
            if container_status:
                container_table.add_row(
                    "Ready",
                    "✅" if container_status.ready else "❌"
                )
                container_table.add_row(
                    "Restart Count",
                    str(container_status.restart_count)
                )
                
                # Estado atual
                state = container_status.state
                if state.running:
                    container_table.add_row("Estado", "🟢 Running")
                elif state.waiting:
                    container_table.add_row("Estado", f"⏳ Waiting ({state.waiting.reason})")
                elif state.terminated:
                    container_table.add_row("Estado", f"⭕ Terminated ({state.terminated.reason})")
            
            console.print()
            console.print(container_table)
        
        # Volumes
        if pod.spec.volumes:
            volume_table = Table(show_header=True, header_style="bold magenta", title="\n💾 Volumes")
            volume_table.add_column("Nome", style="cyan")
            volume_table.add_column("Tipo", style="yellow")
            volume_table.add_column("Detalhes", style="green")
            
            for volume in pod.spec.volumes:
                volume_type = next((k for k in volume.to_dict().keys() if k != 'name'), "N/A")
                volume_details = getattr(volume, volume_type, None)
                details_str = str(volume_details) if volume_details else "N/A"
                
                volume_table.add_row(
                    volume.name,
                    volume_type,
                    details_str
                )
            
            console.print()
            console.print(volume_table)
        
        # Secrets
        secrets = []
        
        # Procura secrets nos volumes
        if pod.spec.volumes:
            for volume in pod.spec.volumes:
                if hasattr(volume, 'secret') and volume.secret:
                    secrets.append({
                        'nome': volume.secret.secret_name,
                        'tipo': 'Volume',
                        'montagem': volume.name,
                        'opcional': str(volume.secret.optional or False)
                    })
        
        # Procura secrets nas env vars dos containers
        for container in pod.spec.containers:
            if container.env:
                for env in container.env:
                    if env.value_from and env.value_from.secret_key_ref:
                        secrets.append({
                            'nome': env.value_from.secret_key_ref.name,
                            'tipo': 'Env',
                            'montagem': f"{container.name}:{env.name}",
                            'opcional': str(env.value_from.secret_key_ref.optional or False)
                        })
            
            # Procura secrets em envFrom
            if container.env_from:
                for env_from in container.env_from:
                    if env_from.secret_ref:
                        secrets.append({
                            'nome': env_from.secret_ref.name,
                            'tipo': 'EnvFrom',
                            'montagem': container.name,
                            'opcional': str(env_from.secret_ref.optional or False)
                        })
        
        if secrets:
            secrets_table = Table(show_header=True, header_style="bold magenta", title="\n🔒 Secrets")
            secrets_table.add_column("Nome", style="cyan")
            secrets_table.add_column("Tipo", style="yellow")
            secrets_table.add_column("Montagem", style="green")
            secrets_table.add_column("Opcional", style="blue")
            
            for secret in secrets:
                secrets_table.add_row(
                    secret['nome'],
                    secret['tipo'],
                    secret['montagem'],
                    secret['opcional']
                )
            
            console.print()
            console.print(secrets_table)
        
        # Eventos
        console.print("\n🔔 [bold]Eventos Recentes:[/]")
        events = v1.list_namespaced_event(
            namespace,
            field_selector=f'involvedObject.name={selected_pod}'
        )
        
        if events.items:
            event_table = Table(show_header=True, header_style="bold magenta")
            event_table.add_column("Tipo", style="cyan", width=10)
            event_table.add_column("Razão", style="yellow", width=20)
            event_table.add_column("Idade", style="green", width=10)
            event_table.add_column("De", style="blue", width=20)
            event_table.add_column("Mensagem", style="white")
            
            for event in events.items:
                # Calcula a idade do evento
                event_time = event.last_timestamp or event.event_time
                if event_time:
                    event_age = time.time() - event_time.timestamp()
                    if event_age < 60:
                        age_str = f"{int(event_age)}s"
                    elif event_age < 3600:
                        age_str = f"{int(event_age/60)}m"
                    elif event_age < 86400:
                        age_str = f"{int(event_age/3600)}h"
                    else:
                        age_str = f"{int(event_age/86400)}d"
                else:
                    age_str = "N/A"
                
                event_table.add_row(
                    event.type,
                    event.reason,
                    age_str,
                    event.source.component,
                    event.message
                )
            
            console.print()
            console.print(event_table)
        else:
            console.print("  Nenhum evento encontrado")
        
        console.print()  # Linha em branco no final
        
    except Exception as e:
        console.print(f"❌ Erro ao obter detalhes do pod: {str(e)}", style="bold red") 
import click
from rich.console import Console
from rich.table import Table
import inquirer
from kubernetes import client, config
from ..utils.kubernetes import get_pod_metrics, parse_resource_value, format_age

console = Console()

@click.command(name="pod-metrics")
@click.argument('namespace', required=False)
def pod_metrics(namespace=None):
    """Mostra uma análise detalhada dos recursos dos pods."""
    try:
        config.load_kube_config()
        v1 = client.CoreV1Api()
        
        if not namespace:
            available_namespaces = [ns.metadata.name for ns in v1.list_namespace().items]
            
            if not available_namespaces:
                console.print("❌ Nenhum namespace encontrado no cluster.", style="bold red")
                return
                
            available_namespaces.sort()
            
            questions = [
                inquirer.List('namespace',
                             message="Selecione o namespace para ver os recursos",
                             choices=available_namespaces,
                             )
            ]
            answers = inquirer.prompt(questions)
            
            if answers:
                namespace = answers['namespace']
            else:
                return

        console.print(f"\n🔄 Analisando recursos no namespace [bold green]{namespace}[/]...", style="yellow")

        pods = v1.list_namespaced_pod(namespace)
        metrics_dict = get_pod_metrics(namespace)
        
        if not metrics_dict:
            console.print("\n❌ Metrics Server não está disponível.", style="bold red")
            return
        
        table = Table(title=f"📊 Análise de Recursos - Namespace: [bold green]{namespace}[/]", show_header=True)
        table.add_column("Pod", style="cyan")
        table.add_column("CPU Req", justify="right", style="blue")
        table.add_column("CPU Lim", justify="right", style="blue")
        table.add_column("CPU Uso", justify="right", style="green")
        table.add_column("CPU %", justify="right", style="yellow")
        table.add_column("Mem Req", justify="right", style="blue")
        table.add_column("Mem Lim", justify="right", style="blue")
        table.add_column("Mem Uso", justify="right", style="green")
        table.add_column("Mem %", justify="right", style="yellow")

        total_cpu_req = total_cpu_lim = total_cpu_use = 0
        total_mem_req = total_mem_lim = total_mem_use = 0
        
        for pod in pods.items:
            pod_name = pod.metadata.name
            if pod_name not in metrics_dict:
                continue
                
            cpu_req = cpu_lim = mem_req = mem_lim = 0
            
            for container in pod.spec.containers:
                if container.resources:
                    if container.resources.requests:
                        cpu_req += parse_resource_value(container.resources.requests.get('cpu', '0'), 'cpu')
                        mem_req += parse_resource_value(container.resources.requests.get('memory', '0'), 'memory')
                    
                    if container.resources.limits:
                        cpu_lim += parse_resource_value(container.resources.limits.get('cpu', '0'), 'cpu')
                        mem_lim += parse_resource_value(container.resources.limits.get('memory', '0'), 'memory')
            
            cpu_use = int(metrics_dict[pod_name]['cpu'].replace('m', ''))
            mem_use = int(metrics_dict[pod_name]['memory'].replace('Mi', ''))
            
            total_cpu_req += cpu_req
            total_cpu_lim += cpu_lim
            total_cpu_use += cpu_use
            total_mem_req += mem_req
            total_mem_lim += mem_lim
            total_mem_use += mem_use
            
            cpu_percent = f"{(cpu_use / cpu_req * 100):.1f}%" if cpu_req > 0 else "N/A"
            
            if mem_req > 0:
                mem_percent = f"{(mem_use / mem_req * 100):.1f}%"
                if mem_use > mem_req:
                    mem_percent = f"[bold red]⚠️ {(mem_use / mem_req * 100):.1f}%[/]"
            elif mem_use > 0:
                mem_percent = "⚠️ Sem request"
            else:
                mem_percent = "N/A"
            
            table.add_row(
                pod_name,
                f"{cpu_req}m",
                f"{cpu_lim}m" if cpu_lim > 0 else "∞",
                f"{cpu_use}m",
                cpu_percent,
                f"{mem_req}Mi" if mem_req > 0 else "0Mi",
                f"{mem_lim}Mi" if mem_lim > 0 else "∞",
                f"{mem_use}Mi",
                mem_percent
            )

        table.add_section()
        
        if total_cpu_req > 0:
            total_cpu_percent = f"{(total_cpu_use / total_cpu_req * 100):.1f}%"
            if total_cpu_use > total_cpu_req:
                total_cpu_percent = f"[bold red]⚠️ {(total_cpu_use / total_cpu_req * 100):.1f}%[/]"
        else:
            total_cpu_percent = "N/A"
        
        if total_mem_req > 0:
            total_mem_percent = f"{(total_mem_use / total_mem_req * 100):.1f}%"
            if total_mem_use > total_mem_req:
                total_mem_percent = f"[bold red]⚠️ {(total_mem_use / total_mem_req * 100):.1f}%[/]"
        elif total_mem_use > 0:
            total_mem_percent = "⚠️ Sem request"
        else:
            total_mem_percent = "N/A"
        
        table.add_row(
            "[bold red]TOTAL[/]",
            f"[bold]{total_cpu_req}m[/]",
            f"[bold]{total_cpu_lim}m[/]" if total_cpu_lim > 0 else "∞",
            f"[bold]{total_cpu_use}m[/]",
            f"[bold]{total_cpu_percent}[/]",
            f"[bold]{total_mem_req}Mi[/]" if total_mem_req > 0 else "[bold]0Mi[/]",
            f"[bold]{total_mem_lim}Mi[/]" if total_mem_lim > 0 else "∞",
            f"[bold]{total_mem_use}Mi[/]",
            f"[bold]{total_mem_percent}[/]"
        )
        
        console.print()
        console.print(table)
        console.print()
        
        console.print("📈 [bold]Resumo de Utilização:[/]")
        
        if total_cpu_req > 0:
            cpu_percent = total_cpu_use / total_cpu_req * 100
            if cpu_percent > 100:
                console.print(f"• CPU: {total_cpu_use}m usado de {total_cpu_req}m alocado ([bold red]⚠️ {cpu_percent:.1f}% - Acima do alocado[/])")
            else:
                console.print(f"• CPU: {total_cpu_use}m usado de {total_cpu_req}m alocado ({cpu_percent:.1f}%)")
        else:
            console.print(f"• CPU: {total_cpu_use}m usado (Sem request definido)")
        
        if total_mem_req > 0:
            mem_percent = total_mem_use / total_mem_req * 100
            if mem_percent > 100:
                console.print(f"• Memória: {total_mem_use}Mi usado de {total_mem_req}Mi alocado ([bold red]⚠️ {mem_percent:.1f}% - Acima do alocado[/])")
            else:
                console.print(f"• Memória: {total_mem_use}Mi usado de {total_mem_req}Mi alocado ({mem_percent:.1f}%)")
        elif total_mem_use > 0:
            console.print(f"• Memória: {total_mem_use}Mi usado ([bold yellow]⚠️ Sem request definido[/])")
        else:
            console.print("• Memória: Sem uso ou request")
        
        console.print()
        
    except Exception as e:
        console.print(f"❌ Erro ao analisar recursos: {str(e)}", style="bold red")

@click.command(name="all-metrics")
def all_metrics():
    """Mostra uma análise detalhada dos recursos de todos os pods em todos os namespaces."""
    try:
        config.load_kube_config()
        v1 = client.CoreV1Api()
        
        console.print("\n🔄 Analisando recursos de todos os namespaces...", style="yellow")

        namespaces = v1.list_namespace()
        namespaces.items.sort(key=lambda x: x.metadata.name)
        
        table = Table(title="📊 Análise de Recursos - Todos os Namespaces", show_header=True)
        table.add_column("Namespace", style="magenta")
        table.add_column("Pod", style="cyan")
        table.add_column("CPU Req", justify="right", style="blue")
        table.add_column("CPU Lim", justify="right", style="blue")
        table.add_column("CPU Uso", justify="right", style="green")
        table.add_column("CPU %", justify="right", style="yellow")
        table.add_column("Mem Req", justify="right", style="blue")
        table.add_column("Mem Lim", justify="right", style="blue")
        table.add_column("Mem Uso", justify="right", style="green")
        table.add_column("Mem %", justify="right", style="yellow")

        total_cpu_req = total_cpu_lim = total_cpu_use = 0
        total_mem_req = total_mem_lim = total_mem_use = 0
        
        is_first_namespace = True
        
        for ns in namespaces.items:
            namespace = ns.metadata.name
            pods = v1.list_namespaced_pod(namespace)
            metrics_dict = get_pod_metrics(namespace)
            
            if not metrics_dict:
                continue
                
            ns_cpu_req = ns_cpu_lim = ns_cpu_use = 0
            ns_mem_req = ns_mem_lim = ns_mem_use = 0
            
            if not is_first_namespace:
                table.add_section()
            is_first_namespace = False
            
            for pod in pods.items:
                pod_name = pod.metadata.name
                if pod_name not in metrics_dict:
                    continue
                    
                cpu_req = cpu_lim = mem_req = mem_lim = 0
                
                for container in pod.spec.containers:
                    if container.resources:
                        if container.resources.requests:
                            cpu_req += parse_resource_value(container.resources.requests.get('cpu', '0'), 'cpu')
                            mem_req += parse_resource_value(container.resources.requests.get('memory', '0'), 'memory')
                        
                        if container.resources.limits:
                            cpu_lim += parse_resource_value(container.resources.limits.get('cpu', '0'), 'cpu')
                            mem_lim += parse_resource_value(container.resources.limits.get('memory', '0'), 'memory')
                
                cpu_use = int(metrics_dict[pod_name]['cpu'].replace('m', ''))
                mem_use = int(metrics_dict[pod_name]['memory'].replace('Mi', ''))
                
                ns_cpu_req += cpu_req
                ns_cpu_lim += cpu_lim
                ns_cpu_use += cpu_use
                ns_mem_req += mem_req
                ns_mem_lim += mem_lim
                ns_mem_use += mem_use
                
                cpu_percent = f"{(cpu_use / cpu_req * 100):.1f}%" if cpu_req > 0 else "N/A"
                
                if mem_req > 0:
                    mem_percent = f"{(mem_use / mem_req * 100):.1f}%"
                    if mem_use > mem_req:
                        mem_percent = f"[bold red]⚠️ {(mem_use / mem_req * 100):.1f}%[/]"
                elif mem_use > 0:
                    mem_percent = "⚠️ Sem request"
                else:
                    mem_percent = "N/A"
                
                table.add_row(
                    namespace,
                    pod_name,
                    f"{cpu_req}m",
                    f"{cpu_lim}m" if cpu_lim > 0 else "∞",
                    f"{cpu_use}m",
                    cpu_percent,
                    f"{mem_req}Mi" if mem_req > 0 else "0Mi",
                    f"{mem_lim}Mi" if mem_lim > 0 else "∞",
                    f"{mem_use}Mi",
                    mem_percent
                )
            
            total_cpu_req += ns_cpu_req
            total_cpu_lim += ns_cpu_lim
            total_cpu_use += ns_cpu_use
            total_mem_req += ns_mem_req
            total_mem_lim += ns_mem_lim
            total_mem_use += ns_mem_use
            
            if ns_cpu_req > 0 or ns_mem_req > 0 or ns_cpu_use > 0 or ns_mem_use > 0:
                ns_cpu_percent = f"{(ns_cpu_use / ns_cpu_req * 100):.1f}%" if ns_cpu_req > 0 else "N/A"
                
                if ns_mem_req > 0:
                    ns_mem_percent = f"{(ns_mem_use / ns_mem_req * 100):.1f}%"
                    if ns_mem_use > ns_mem_req:
                        ns_mem_percent = f"[bold red]⚠️ {(ns_mem_use / ns_mem_req * 100):.1f}%[/]"
                elif ns_mem_use > 0:
                    ns_mem_percent = "⚠️ Sem request"
                else:
                    ns_mem_percent = "N/A"
                
                table.add_row(
                    f"[bold]{namespace}[/]",
                    "[bold]Total[/]",
                    f"[bold]{ns_cpu_req}m[/]",
                    f"[bold]{ns_cpu_lim}m[/]" if ns_cpu_lim > 0 else "∞",
                    f"[bold]{ns_cpu_use}m[/]",
                    f"[bold]{ns_cpu_percent}[/]",
                    f"[bold]{ns_mem_req}Mi[/]" if ns_mem_req > 0 else "[bold]0Mi[/]",
                    f"[bold]{ns_mem_lim}Mi[/]" if ns_mem_lim > 0 else "∞",
                    f"[bold]{ns_mem_use}Mi[/]",
                    f"[bold]{ns_mem_percent}[/]"
                )

        table.add_section()
        
        if total_cpu_req > 0:
            total_cpu_percent = f"{(total_cpu_use / total_cpu_req * 100):.1f}%"
            if total_cpu_use > total_cpu_req:
                total_cpu_percent = f"[bold red]⚠️ {(total_cpu_use / total_cpu_req * 100):.1f}%[/]"
        else:
            total_cpu_percent = "N/A"
        
        if total_mem_req > 0:
            total_mem_percent = f"{(total_mem_use / total_mem_req * 100):.1f}%"
            if total_mem_use > total_mem_req:
                total_mem_percent = f"[bold red]⚠️ {(total_mem_use / total_mem_req * 100):.1f}%[/]"
        elif total_mem_use > 0:
            total_mem_percent = "⚠️ Sem request"
        else:
            total_mem_percent = "N/A"
        
        table.add_row(
            "[bold red]TOTAL GERAL[/]",
            "",
            f"[bold]{total_cpu_req}m[/]",
            f"[bold]{total_cpu_lim}m[/]" if total_cpu_lim > 0 else "∞",
            f"[bold]{total_cpu_use}m[/]",
            f"[bold]{total_cpu_percent}[/]",
            f"[bold]{total_mem_req}Mi[/]" if total_mem_req > 0 else "[bold]0Mi[/]",
            f"[bold]{total_mem_lim}Mi[/]" if total_mem_lim > 0 else "∞",
            f"[bold]{total_mem_use}Mi[/]",
            f"[bold]{total_mem_percent}[/]"
        )
        
        console.print()
        console.print(table)
        console.print()
        
        console.print("📈 [bold]Resumo de Utilização Total:[/]")
        
        if total_cpu_req > 0:
            cpu_percent = total_cpu_use / total_cpu_req * 100
            if cpu_percent > 100:
                console.print(f"• CPU: {total_cpu_use}m usado de {total_cpu_req}m alocado ([bold red]⚠️ {cpu_percent:.1f}% - Acima do alocado[/])")
            else:
                console.print(f"• CPU: {total_cpu_use}m usado de {total_cpu_req}m alocado ({cpu_percent:.1f}%)")
        else:
            console.print(f"• CPU: {total_cpu_use}m usado (Sem request definido)")
        
        if total_mem_req > 0:
            mem_percent = total_mem_use / total_mem_req * 100
            if mem_percent > 100:
                console.print(f"• Memória: {total_mem_use}Mi usado de {total_mem_req}Mi alocado ([bold red]⚠️ {mem_percent:.1f}% - Acima do alocado[/])")
            else:
                console.print(f"• Memória: {total_mem_use}Mi usado de {total_mem_req}Mi alocado ({mem_percent:.1f}%)")
        elif total_mem_use > 0:
            console.print(f"• Memória: {total_mem_use}Mi usado ([bold yellow]⚠️ Sem request definido[/])")
        else:
            console.print("• Memória: Sem uso ou request")
        
        console.print()
        
    except Exception as e:
        console.print(f"❌ Erro ao analisar recursos: {str(e)}", style="bold red") 
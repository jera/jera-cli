import click
from rich.console import Console
from rich.table import Table
import subprocess
from ..utils.common import load_namespace

console = Console()

@click.command()
@click.option('--namespace', '-n', help='Filtra por namespace específico')
def urls(namespace=None):
    """Mostra as URLs dos Ingress disponíveis no cluster.
    
    Por padrão, mostra Ingress de todos os namespaces.
    Use a opção --namespace para filtrar por um namespace específico.
    
    Exemplos:
        $ jcli urls                    # Mostra URLs de todos os namespaces
        $ jcli urls -n production      # Mostra URLs apenas do namespace production
    """
    try:
        # Se foi especificado um namespace, usa ele
        # Caso contrário, mostra todos os namespaces por padrão
        selected_namespace = namespace
        show_all = selected_namespace is None
        
        # Se não especificou namespace, usa o configurado apenas para mostrar no cabeçalho
        configured_namespace = None
        if not selected_namespace and not show_all:
            configured_namespace = load_namespace()
            selected_namespace = configured_namespace

        # Executa o comando kubectl para obter os Ingresses
        cmd = ["kubectl", "get", "ingress"]
        
        if selected_namespace:
            cmd.extend(["-n", selected_namespace])
        else:
            cmd.append("--all-namespaces")
            
        cmd.extend(["-o", "json"])
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            # Tenta verificar se o erro é por falta de recursos Ingress
            if "No resources found" in result.stderr:
                if show_all:
                    console.print("ℹ️ Nenhum Ingress encontrado em nenhum namespace.", style="bold yellow")
                else:
                    console.print(f"ℹ️ Nenhum Ingress encontrado no namespace '{selected_namespace}'.", style="bold yellow")
                return
            else:
                console.print(f"❌ Erro ao obter Ingresses: {result.stderr}", style="bold red")
                return
        
        import json
        ingresses = json.loads(result.stdout)
        
        # Se não houver Ingresses
        if not ingresses.get('items'):
            if show_all:
                console.print("ℹ️ Nenhum Ingress encontrado em nenhum namespace.", style="bold yellow")
            else:
                console.print(f"ℹ️ Nenhum Ingress encontrado no namespace '{selected_namespace}'.", style="bold yellow")
            return
        
        # Cria a tabela para exibir os resultados
        table = Table(show_header=True, header_style="bold magenta")
        
        if show_all:
            table.add_column("Namespace", style="blue")
        
        table.add_column("Nome", style="cyan")
        table.add_column("URL", style="bold white")
        table.add_column("Backend", style="dim")
        
        # Processa cada Ingress
        for ingress in ingresses['items']:
            ingress_name = ingress['metadata']['name']
            ingress_namespace = ingress['metadata']['namespace']
            
            # Pula ingresses de outros namespaces se um foi especificado
            if selected_namespace and ingress_namespace != selected_namespace:
                continue
            
            # Obtém o endereço do LoadBalancer (não usado na tabela, mas mantido para reuso no futuro)
            lb_address = "N/A"
            if 'status' in ingress and 'loadBalancer' in ingress['status']:
                ingress_lb = ingress['status']['loadBalancer']
                if 'ingress' in ingress_lb and ingress_lb['ingress']:
                    lb_entry = ingress_lb['ingress'][0]
                    lb_address = lb_entry.get('hostname') or lb_entry.get('ip') or "N/A"
            
            # Extrai as regras
            if 'rules' not in ingress['spec']:
                # Ingress sem regras, possivelmente apenas com TLS ou defaultBackend
                if show_all:
                    table.add_row(
                        ingress_namespace,
                        ingress_name,
                        "N/A",
                        "DefaultBackend"
                    )
                else:
                    table.add_row(
                        ingress_name,
                        "N/A",
                        "DefaultBackend"
                    )
                continue
            
            # Processa todas as regras e caminhos
            for rule in ingress['spec']['rules']:
                host = rule.get('host', '*')
                
                if 'http' not in rule:
                    # Regra sem HTTP paths (possivelmente apenas DNS)
                    if show_all:
                        table.add_row(
                            ingress_namespace,
                            ingress_name,
                            f"https://{host}",
                            "N/A"
                        )
                    else:
                        table.add_row(
                            ingress_name,
                            f"https://{host}",
                            "N/A"
                        )
                    continue
                
                # Processa os caminhos HTTP
                for path in rule['http']['paths']:
                    path_value = path.get('path', '/')
                    
                    # Determina o serviço backend
                    if 'backend' in path:
                        # Formato antigo (v1)
                        if 'serviceName' in path['backend']:
                            backend = f"{path['backend']['serviceName']}:{path['backend'].get('servicePort', 'N/A')}"
                        # Formato novo (v1beta1 ou v1)
                        elif 'service' in path['backend']:
                            service_info = path['backend']['service']
                            backend = f"{service_info['name']}:{service_info.get('port', {}).get('number', 'N/A')}"
                        else:
                            backend = "N/A"
                    else:
                        backend = "N/A"
                    
                    # Gera a URL completa
                    url = f"https://{host}{path_value}"
                    
                    # Adiciona à tabela
                    if show_all:
                        table.add_row(
                            ingress_namespace,
                            ingress_name,
                            url,
                            backend
                        )
                    else:
                        table.add_row(
                            ingress_name,
                            url,
                            backend
                        )
        
        # Título da tabela
        if show_all:
            console.print("\n🌐 URLs de Ingress (todos os namespaces):", style="bold blue")
        else:
            console.print(f"\n🌐 URLs de Ingress no namespace [bold green]{selected_namespace}[/]:", style="bold blue")
        
        # Imprime a tabela
        console.print(table)
        
        # Nota adicional sobre HTTPS
        console.print("\nNota: As URLs são mostradas com http:// por padrão. Se o Ingress estiver configurado para HTTPS, substitua por https://.", style="dim")
            
    except Exception as e:
        console.print(f"❌ Erro ao listar URLs de Ingress: {str(e)}", style="bold red")

@click.command()
@click.option('--namespace', '-n', help='Filtra por namespace específico')
def loadbalancer(namespace=None):
    """Mostra as URLs dos LoadBalancers dos Ingress no cluster.
    
    Por padrão, mostra os LoadBalancers de todos os namespaces.
    Use a opção --namespace para filtrar por um namespace específico.
    
    Exemplos:
        $ jcli loadbalancer                # Mostra LoadBalancers de todos os namespaces
        $ jcli loadbalancer -n production  # Mostra LoadBalancers apenas do namespace production
    """
    try:
        # Se foi especificado um namespace, usa ele
        # Caso contrário, mostra todos os namespaces por padrão
        selected_namespace = namespace
        show_all = selected_namespace is None
        
        # Se não especificou namespace, usa o configurado apenas para mostrar no cabeçalho
        configured_namespace = None
        if not selected_namespace and not show_all:
            configured_namespace = load_namespace()
            selected_namespace = configured_namespace

        # Executa o comando kubectl para obter os Ingresses
        cmd = ["kubectl", "get", "ingress"]
        
        if selected_namespace:
            cmd.extend(["-n", selected_namespace])
        else:
            cmd.append("--all-namespaces")
            
        cmd.extend(["-o", "json"])
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            # Tenta verificar se o erro é por falta de recursos Ingress
            if "No resources found" in result.stderr:
                if show_all:
                    console.print("ℹ️ Nenhum Ingress encontrado em nenhum namespace.", style="bold yellow")
                else:
                    console.print(f"ℹ️ Nenhum Ingress encontrado no namespace '{selected_namespace}'.", style="bold yellow")
                return
            else:
                console.print(f"❌ Erro ao obter Ingresses: {result.stderr}", style="bold red")
                return
        
        import json
        ingresses = json.loads(result.stdout)
        
        # Se não houver Ingresses
        if not ingresses.get('items'):
            if show_all:
                console.print("ℹ️ Nenhum Ingress encontrado em nenhum namespace.", style="bold yellow")
            else:
                console.print(f"ℹ️ Nenhum Ingress encontrado no namespace '{selected_namespace}'.", style="bold yellow")
            return
        
        # Cria a tabela para exibir os resultados
        table = Table(show_header=True, header_style="bold magenta")
        
        # Inverte a lógica: agora agrupa por URL e lista namespaces associados
        if show_all:
            table.add_column("LoadBalancer URL", style="bold green")
            table.add_column("Namespaces", style="blue")
        else:
            table.add_column("LoadBalancer URL", style="bold green")
        
        # Dicionário para agrupar namespaces por URL de LoadBalancer
        urls_to_namespaces = {}
        
        # Processa cada Ingress para encontrar os LoadBalancers
        for ingress in ingresses['items']:
            ingress_name = ingress['metadata']['name']
            ingress_namespace = ingress['metadata']['namespace']
            
            # Pula ingresses de outros namespaces se um foi especificado
            if selected_namespace and ingress_namespace != selected_namespace:
                continue
            
            # Obtém o endereço do LoadBalancer
            if 'status' in ingress and 'loadBalancer' in ingress['status']:
                ingress_lb = ingress['status']['loadBalancer']
                if 'ingress' in ingress_lb and ingress_lb['ingress']:
                    lb_entry = ingress_lb['ingress'][0]
                    
                    # Verifica se temos um hostname ou IP
                    hostname = lb_entry.get('hostname')
                    ip = lb_entry.get('ip')
                    
                    # Formata a URL do LoadBalancer
                    lb_address = None
                    if hostname:
                        lb_address = f"https://{hostname}"
                    elif ip:
                        lb_address = f"https://{ip}"
                        
                    if lb_address:
                        # Agrupa namespaces por URL
                        if lb_address not in urls_to_namespaces:
                            urls_to_namespaces[lb_address] = set()
                        
                        # Se estamos mostrando todos os namespaces, adiciona este namespace à lista
                        if show_all:
                            urls_to_namespaces[lb_address].add(ingress_namespace)
        
        # Verifica se encontrou algum LoadBalancer
        found_lb = len(urls_to_namespaces) > 0
        
        # Se não encontrou nenhum LoadBalancer
        if not found_lb:
            if show_all:
                console.print("ℹ️ Nenhum LoadBalancer encontrado em nenhum namespace.", style="bold yellow")
            else:
                console.print(f"ℹ️ Nenhum LoadBalancer encontrado no namespace '{selected_namespace}'.", style="bold yellow")
            return
        
        # Título da tabela
        if show_all:
            console.print("\n🌐 URLs dos LoadBalancers (agrupados):", style="bold blue")
        else:
            console.print(f"\n🌐 URLs dos LoadBalancers no namespace [bold green]{selected_namespace}[/]:", style="bold blue")
        
        # Imprime as URLs primeiro, sem tabela, para garantir que sejam exibidas por completo
        for url, namespaces in urls_to_namespaces.items():
            console.print(f"\n[bold green]{url}[/]")
            
            # Se estamos mostrando todos os namespaces, exibe a lista
            if show_all:
                # Agrupa namespaces em linhas de no máximo 80 caracteres
                namespaces_list = sorted(namespaces)
                line = "  [blue]Namespaces:[/] "
                for ns in namespaces_list:
                    # Se adicionar este namespace ultrapassar o limite, imprime a linha atual e começa nova linha
                    if len(line + ns) > 100:
                        console.print(line)
                        line = "    "
                    
                    line += ns + ", "
                
                # Imprime a última linha, removendo a vírgula final
                if line.endswith(", "):
                    line = line[:-2]
                if line.strip():
                    console.print(line)
        
        # Nota adicional sobre HTTPS
        console.print("\nNota: As URLs são mostradas com https:// por padrão.", style="dim")
            
    except Exception as e:
        console.print(f"❌ Erro ao listar URLs dos LoadBalancers: {str(e)}", style="bold red") 
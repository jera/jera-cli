import click
from rich.console import Console
from rich.table import Table
from kubernetes import client, config
import inquirer
import time

console = Console()

@click.command()
@click.argument('namespace', required=False)
@click.argument('ingress_name', required=False)
def url(namespace=None, ingress_name=None):
    """Mostra as URLs dos Ingresses.
    
    Se o namespace não for fornecido, apresenta uma lista interativa
    de namespaces disponíveis. Mostra informações básicas dos Ingresses:
    - Nome do Ingress
    - Hosts configurados
    - Endereço do LoadBalancer
    - Portas disponíveis
    
    Exemplos:
        $ jeracli url                      # Seleciona namespace interativamente
        $ jeracli url production           # Mostra todos os Ingresses do namespace
        $ jeracli url production meu-app   # Mostra URLs do Ingress específico
    """
    try:
        config.load_kube_config()
        v1 = client.CoreV1Api()
        networking_v1 = client.NetworkingV1Api()
        
        # Se não foi fornecido um namespace, mostra a lista interativa
        if not namespace:
            available_namespaces = [ns.metadata.name for ns in v1.list_namespace().items]
            
            if not available_namespaces:
                console.print("❌ Nenhum namespace encontrado no cluster.", style="bold red")
                return
                
            # Ordena os namespaces alfabeticamente
            available_namespaces.sort()
            
            questions = [
                inquirer.List('namespace',
                             message="Selecione o namespace",
                             choices=available_namespaces,
                             )
            ]
            answers = inquirer.prompt(questions)
            
            if answers:
                namespace = answers['namespace']
            else:
                return

        # Mostra mensagem de conexão
        console.print(f"\n🔄 Conectando ao namespace [bold green]{namespace}[/] e buscando Ingresses...", style="yellow")

        # Lista todos os Ingresses no namespace
        ingresses = networking_v1.list_namespaced_ingress(namespace)
        
        if not ingresses.items:
            console.print(f"\n❌ Nenhum Ingress encontrado no namespace [bold green]{namespace}[/]", style="bold red")
            return

        # Se forneceu um nome específico, filtra apenas o Ingress solicitado
        if ingress_name:
            ingresses.items = [ing for ing in ingresses.items if ing.metadata.name == ingress_name]
            if not ingresses.items:
                console.print(f"\n❌ Ingress [bold cyan]{ingress_name}[/] não encontrado no namespace [bold green]{namespace}[/]", style="bold red")
                return

        # Cria uma tabela rica para exibir os Ingresses
        table = Table(title=f"🌐 Ingresses em [bold green]{namespace}[/]", show_header=True)
        table.add_column("Nome", style="cyan")
        table.add_column("Hosts", style="yellow")
        table.add_column("Endereço", style="green")
        table.add_column("Portas", style="blue", justify="right")
        table.add_column("Idade", style="magenta", justify="right")
        
        # Para cada Ingress, adiciona uma linha na tabela
        for ing in ingresses.items:
            # Obtém os hosts
            hosts = []
            if ing.spec.rules:
                hosts = [rule.host for rule in ing.spec.rules if rule.host]
            hosts_str = ",".join(hosts) if hosts else "*"
            
            # Obtém o endereço do LoadBalancer
            address = ""
            if ing.status.load_balancer.ingress:
                address = ing.status.load_balancer.ingress[0].hostname or ing.status.load_balancer.ingress[0].ip or ""
            
            # Obtém as portas (do TLS e HTTP)
            ports = set()
            if ing.spec.tls:
                ports.add("443")
            ports.add("80")  # HTTP é sempre habilitado
            ports_str = ", ".join(sorted(ports))
            
            # Calcula a idade
            creation_time = ing.metadata.creation_timestamp
            age = time.time() - creation_time.timestamp()
            if age < 3600:  # menos de 1 hora
                age_str = f"{int(age/60)}m"
            elif age < 86400:  # menos de 1 dia
                age_str = f"{int(age/3600)}h"
            else:
                age_str = f"{int(age/86400)}d"
            
            table.add_row(
                ing.metadata.name,
                hosts_str,
                address,
                ports_str,
                age_str
            )
        
        # Mostra a tabela
        console.print()
        console.print(table)
        console.print()
        
    except Exception as e:
        console.print(f"❌ Erro ao obter URLs dos Ingresses: {str(e)}", style="bold red") 
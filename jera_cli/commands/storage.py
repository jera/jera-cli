import click
from rich.console import Console
from rich.table import Table
import subprocess
import json
import inquirer
from ..utils.common import load_namespace

console = Console()

@click.command()
@click.option('--namespace', '-n', help='Filtra por namespace específico')
@click.option('--select', '-s', is_flag=True, help='Seleciona o namespace interativamente')
def pvcs(namespace=None, select=False):
    """Mostra os Persistent Volume Claims (PVCs) no cluster.
    
    Por padrão, mostra PVCs de todos os namespaces.
    Use a opção --namespace para filtrar por um namespace específico,
    ou use --select para escolher o namespace interativamente.
    
    Exemplos:
        $ jcli pvcs                    # Mostra PVCs de todos os namespaces
        $ jcli pvcs -n production      # Mostra PVCs do namespace production
        $ jcli pvcs -s                 # Seleciona o namespace interativamente
    """
    try:
        # Se foi pedido para selecionar o namespace interativamente
        if select:
            # Lista todos os namespaces disponíveis
            ns_cmd = ["kubectl", "get", "namespaces", "-o", "json"]
            ns_result = subprocess.run(
                ns_cmd,
                capture_output=True,
                text=True,
                check=False
            )
            
            if ns_result.returncode != 0:
                console.print(f"❌ Erro ao listar namespaces: {ns_result.stderr}", style="bold red")
                return
                
            namespaces_json = json.loads(ns_result.stdout)
            namespaces = [item['metadata']['name'] for item in namespaces_json['items']]
            namespaces.sort()
            
            # Adiciona opção para todos os namespaces
            namespaces.insert(0, "* Todos os namespaces")
            
            # Permite selecionar o namespace
            questions = [
                inquirer.List('namespace',
                             message="Selecione o namespace",
                             choices=namespaces,
                             )
            ]
            answers = inquirer.prompt(questions)
            
            if answers:
                if answers['namespace'] == "* Todos os namespaces":
                    namespace = None
                else:
                    namespace = answers['namespace']
            else:
                return

        # Se foi especificado um namespace ou selecionado interativamente
        show_all = namespace is None
        
        # Executa o comando kubectl para obter os PVCs
        cmd = ["kubectl", "get", "pvc"]
        
        if namespace:
            cmd.extend(["-n", namespace])
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
            # Verifica se o erro é por falta de recursos
            if "No resources found" in result.stderr:
                if show_all:
                    console.print("ℹ️ Nenhum PVC encontrado em nenhum namespace.", style="bold yellow")
                else:
                    console.print(f"ℹ️ Nenhum PVC encontrado no namespace '{namespace}'.", style="bold yellow")
                return
            else:
                console.print(f"❌ Erro ao obter PVCs: {result.stderr}", style="bold red")
                return
        
        pvcs_json = json.loads(result.stdout)
        
        # Se não houver PVCs
        if not pvcs_json.get('items'):
            if show_all:
                console.print("ℹ️ Nenhum PVC encontrado em nenhum namespace.", style="bold yellow")
            else:
                console.print(f"ℹ️ Nenhum PVC encontrado no namespace '{namespace}'.", style="bold yellow")
            return
        
        # Cria a tabela para exibir os resultados
        table = Table(show_header=True, header_style="bold magenta")
        
        if show_all:
            table.add_column("Namespace", style="blue")
        
        table.add_column("Nome", style="cyan")
        table.add_column("Status", style="yellow")
        table.add_column("Volume", style="green")
        table.add_column("Capacidade", style="bold white")
        table.add_column("Modo de Acesso", style="dim")
        table.add_column("StorageClass", style="dim")
        table.add_column("Idade", style="dim")
        
        # Processa cada PVC
        for pvc in pvcs_json['items']:
            pvc_name = pvc['metadata']['name']
            pvc_namespace = pvc['metadata']['namespace']
            
            # Obtém o status
            status = pvc['status']['phase']
            status_style = "green" if status == "Bound" else "yellow" if status == "Pending" else "red"
            status_formatted = f"[{status_style}]{status}[/{status_style}]"
            
            # Volume vinculado
            volume = pvc['spec'].get('volumeName', 'N/A')
            
            # Capacidade solicitada
            capacity = pvc['spec']['resources']['requests'].get('storage', 'N/A')
            
            # Modos de acesso
            access_modes = ", ".join(pvc['spec'].get('accessModes', ['N/A']))
            
            # StorageClass
            storage_class = pvc['spec'].get('storageClassName', 'default')
            
            # Idade - cálculo simplificado
            from datetime import datetime
            creation_time = datetime.fromisoformat(pvc['metadata']['creationTimestamp'].replace('Z', '+00:00'))
            now = datetime.now().astimezone()
            age_seconds = (now - creation_time).total_seconds()
            
            if age_seconds < 3600:  # menos de 1 hora
                age = f"{int(age_seconds / 60)}m"
            elif age_seconds < 86400:  # menos de 1 dia
                age = f"{int(age_seconds / 3600)}h"
            else:
                age = f"{int(age_seconds / 86400)}d"
            
            # Adiciona à tabela
            if show_all:
                table.add_row(
                    pvc_namespace,
                    pvc_name,
                    status_formatted,
                    volume,
                    capacity,
                    access_modes,
                    storage_class,
                    age
                )
            else:
                table.add_row(
                    pvc_name,
                    status_formatted,
                    volume,
                    capacity,
                    access_modes,
                    storage_class,
                    age
                )
        
        # Título da tabela
        if show_all:
            console.print("\n💾 Persistent Volume Claims (todos os namespaces):", style="bold blue")
        else:
            console.print(f"\n💾 Persistent Volume Claims no namespace [bold green]{namespace}[/]:", style="bold blue")
        
        # Imprime a tabela
        console.print(table)
            
    except Exception as e:
        console.print(f"❌ Erro ao listar PVCs: {str(e)}", style="bold red")

@click.command()
@click.option('--detailed', '-d', is_flag=True, help='Exibe informações detalhadas sobre os volumes')
def pvs(detailed=False):
    """Mostra os Persistent Volumes (PVs) no cluster.
    
    Os PVs são recursos globais no Kubernetes e não pertencem a namespaces.
    Use a opção --detailed para ver informações mais detalhadas sobre cada volume.
    
    Exemplos:
        $ jcli pvs                # Mostra lista básica de PVs
        $ jcli pvs -d             # Mostra detalhes dos PVs
    """
    try:
        # Executa o comando kubectl para obter os PVs
        cmd = ["kubectl", "get", "pv", "-o", "json"]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            # Verifica se o erro é por falta de recursos
            if "No resources found" in result.stderr:
                console.print("ℹ️ Nenhum Persistent Volume encontrado no cluster.", style="bold yellow")
                return
            else:
                console.print(f"❌ Erro ao obter PVs: {result.stderr}", style="bold red")
                return
        
        pvs_json = json.loads(result.stdout)
        
        # Se não houver PVs
        if not pvs_json.get('items'):
            console.print("ℹ️ Nenhum Persistent Volume encontrado no cluster.", style="bold yellow")
            return
        
        # Cria a tabela para exibir os resultados
        table = Table(show_header=True, header_style="bold magenta")
        
        table.add_column("Nome", style="cyan")
        table.add_column("Status", style="yellow")
        table.add_column("Capacidade", style="bold white")
        table.add_column("Modo de Acesso", style="dim")
        table.add_column("StorageClass", style="dim")
        table.add_column("Reclaim Policy", style="dim")
        
        if detailed:
            table.add_column("PVC", style="blue")
            table.add_column("Namespace", style="blue")
            table.add_column("Tipo de Volume", style="green")
        
        # Processa cada PV
        for pv in pvs_json['items']:
            pv_name = pv['metadata']['name']
            
            # Obtém o status
            status = pv['status']['phase']
            status_style = "green" if status == "Bound" else "yellow" if status in ["Available", "Released"] else "red"
            status_formatted = f"[{status_style}]{status}[/{status_style}]"
            
            # Capacidade
            capacity = pv['spec']['capacity'].get('storage', 'N/A')
            
            # Modos de acesso
            access_modes = ", ".join(pv['spec'].get('accessModes', ['N/A']))
            
            # StorageClass
            storage_class = pv['spec'].get('storageClassName', 'N/A')
            
            # Política de reclaim
            reclaim_policy = pv['spec'].get('persistentVolumeReclaimPolicy', 'N/A')
            
            # Para visualização detalhada
            if detailed:
                # PVC vinculado
                pvc = "N/A"
                namespace = "N/A"
                if status == "Bound" and 'claimRef' in pv:
                    pvc = pv['spec']['claimRef'].get('name', 'N/A')
                    namespace = pv['spec']['claimRef'].get('namespace', 'N/A')
                
                # Tipo de volume (primeira chave após volumeType no spec, como awsElasticBlockStore, hostPath, etc)
                volume_types = [k for k in pv['spec'].keys() if k not in 
                               ['accessModes', 'capacity', 'claimRef', 'persistentVolumeReclaimPolicy', 
                                'storageClassName', 'volumeMode']]
                volume_type = volume_types[0] if volume_types else "N/A"
                
                table.add_row(
                    pv_name,
                    status_formatted,
                    capacity,
                    access_modes,
                    storage_class,
                    reclaim_policy,
                    pvc,
                    namespace,
                    volume_type
                )
            else:
                table.add_row(
                    pv_name,
                    status_formatted,
                    capacity,
                    access_modes,
                    storage_class,
                    reclaim_policy
                )
        
        # Título da tabela
        if detailed:
            console.print("\n💾 Persistent Volumes (detalhado):", style="bold blue")
        else:
            console.print("\n💾 Persistent Volumes:", style="bold blue")
        
        # Imprime a tabela
        console.print(table)
            
    except Exception as e:
        console.print(f"❌ Erro ao listar PVs: {str(e)}", style="bold red")

@click.command()
@click.option('--namespace', '-n', help='Filtra por namespace específico')
@click.option('--select', '-s', is_flag=True, help='Seleciona o namespace interativamente')
@click.option('--detailed', '-d', is_flag=True, help='Exibe informações detalhadas sobre os volumes')
def storage(namespace=None, select=False, detailed=False):
    """Mostra informações sobre armazenamento no cluster (PVs e PVCs).
    
    Combina as informações de PVs e PVCs em uma visão consolidada.
    Por padrão, mostra PVCs de todos os namespaces e todos os PVs.
    
    Exemplos:
        $ jcli storage                 # Visão geral de armazenamento
        $ jcli storage -n production   # Filtra PVCs por namespace
        $ jcli storage -s              # Seleciona o namespace interativamente
        $ jcli storage -d              # Mostra detalhes adicionais
    """
    try:
        # Reutiliza a mesma lógica dos comandos pvs e pvcs
        # Primeiro, chama a lógica para obter os PVCs
        pvcs_cmd = ["kubectl", "get", "pvc"]
        
        # Se foi pedido para selecionar o namespace interativamente
        if select:
            # Lista todos os namespaces disponíveis
            ns_cmd = ["kubectl", "get", "namespaces", "-o", "json"]
            ns_result = subprocess.run(
                ns_cmd,
                capture_output=True,
                text=True,
                check=False
            )
            
            if ns_result.returncode != 0:
                console.print(f"❌ Erro ao listar namespaces: {ns_result.stderr}", style="bold red")
                return
                
            namespaces_json = json.loads(ns_result.stdout)
            namespaces = [item['metadata']['name'] for item in namespaces_json['items']]
            namespaces.sort()
            
            # Adiciona opção para todos os namespaces
            namespaces.insert(0, "* Todos os namespaces")
            
            # Permite selecionar o namespace
            questions = [
                inquirer.List('namespace',
                             message="Selecione o namespace",
                             choices=namespaces,
                             )
            ]
            answers = inquirer.prompt(questions)
            
            if answers:
                if answers['namespace'] == "* Todos os namespaces":
                    namespace = None
                else:
                    namespace = answers['namespace']
            else:
                return

        # Se foi especificado um namespace ou selecionado interativamente
        show_all_ns = namespace is None
        
        console.print("\n🔍 Analisando recursos de armazenamento...", style="bold blue")
        
        # Primeiro, imprime os PVs
        console.print("\n=== Persistent Volumes ===", style="bold cyan")
        pvs(detailed)
        
        # Em seguida, imprime os PVCs
        if show_all_ns:
            console.print("\n=== Persistent Volume Claims (todos os namespaces) ===", style="bold cyan")
        else:
            console.print(f"\n=== Persistent Volume Claims (namespace: {namespace}) ===", style="bold cyan")
            
        pvcs(namespace, select=False)  # não queremos selecionar novamente
        
    except Exception as e:
        console.print(f"❌ Erro ao analisar armazenamento: {str(e)}", style="bold red") 
import click
from rich.console import Console
import inquirer
import yaml
import os
from kubernetes import client, config
import subprocess
import json
from rich.table import Table
from ..utils.kubernetes import check_aws_sso_config, check_aws_sso_session

console = Console()

@click.command()
@click.option('--cluster', '-c', help='Nome do cluster EKS para inicializar')
@click.option('--region', '-r', default='us-east-1', help='Região AWS onde o cluster está localizado')
@click.option('--profile', '-p', help='Profile AWS para usar')
def init(cluster=None, region='us-east-1', profile=None):
    """Inicializa a configuração do kubectl para um cluster EKS."""
    try:
        # Verifica se o AWS CLI está instalado
        try:
            result = subprocess.run(["aws", "--version"], capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception("AWS CLI não encontrado")
        except:
            console.print("\n❌ AWS CLI não está instalado!", style="bold red")
            console.print("\n📝 Para instalar o AWS CLI:", style="bold yellow")
            console.print("1. Linux/MacOS:", style="dim")
            console.print("   https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html")
            console.print("\n2. Windows:", style="dim")
            console.print("   https://aws.amazon.com/cli/")
            console.print("\nInstale o AWS CLI e tente novamente.", style="bold yellow")
            return

        # Verifica se tem uma sessão AWS ativa
        if not check_aws_sso_session():
            console.print("\n⚠️  Você não tem uma sessão AWS SSO ativa!", style="bold yellow")
            console.print("\n📝 Siga os passos abaixo para configurar e autenticar:", style="bold blue")
            console.print("\n1. Configure o AWS SSO (se ainda não configurou):", style="bold white")
            console.print("   aws configure sso", style="bold green")
            console.print("   Dicas para configuração:", style="dim white")
            console.print("   - SSO start URL: https://jera.awsapps.com/start", style="dim white")
            console.print("   - SSO Region: us-east-1", style="dim white")
            console.print("   - CLI default client Region: us-east-1", style="dim white")
            console.print("   - CLI default output format: json", style="dim white")
            console.print("   - CLI profile name: seu-nome", style="dim white")
            
            console.print("\n2. Faça login no AWS SSO:", style="bold white")
            console.print("   aws sso login --profile seu-profile", style="bold green")
            
            console.print("\nExecute o comando 'jeracli init' novamente após completar os passos acima.", style="bold blue")
            return

        # Lista os profiles disponíveis
        result = subprocess.run(
            ["aws", "configure", "list-profiles"],
            capture_output=True,
            text=True
        )
        profiles = result.stdout.strip().split('\n')
        
        selected_profile = profile
        
        # Se não foi fornecido um profile, mostra a lista interativa
        if not selected_profile:
            questions = [
                inquirer.List('profile',
                             message="Selecione o profile AWS para usar",
                             choices=profiles,
                             )
            ]
            answers = inquirer.prompt(questions)
            
            if answers:
                selected_profile = answers['profile']
            else:
                return
        
        # Se não foi fornecido cluster, lista os clusters disponíveis
        selected_cluster = cluster
        if not selected_cluster:
            console.print(f"🔍 Listando clusters EKS disponíveis com profile '{selected_profile}'...", style="bold blue")
            
            try:
                result = subprocess.run(
                    ["aws", "eks", "list-clusters", "--region", region, "--profile", selected_profile],
                    capture_output=True,
                    text=True,
                    check=True
                )
                clusters_data = json.loads(result.stdout)
                available_clusters = clusters_data.get("clusters", [])
                
                if not available_clusters:
                    console.print("❌ Nenhum cluster EKS encontrado na conta.", style="bold red")
                    return
                
                questions = [
                    inquirer.List('cluster',
                                message="Selecione um cluster EKS para inicializar",
                                choices=available_clusters,
                                )
                ]
                answers = inquirer.prompt(questions)
                
                if answers:
                    selected_cluster = answers['cluster']
                else:
                    return
            except Exception as e:
                console.print(f"❌ Erro ao listar clusters: {str(e)}", style="bold red")
                return
        
        # Tenta usar o profile para atualizar o kubeconfig
        console.print(f"🔄 Atualizando kubeconfig para o cluster '{selected_cluster}' com profile '{selected_profile}'...", style="bold blue")
        try:
            subprocess.run([
                "aws", "eks", "update-kubeconfig",
                "--name", selected_cluster,
                "--region", region,
                "--profile", selected_profile
            ], check=True)
            
            # Atualiza a configuração para o cluster atual
            os.makedirs(os.path.expanduser('~/.jera'), exist_ok=True)
            config_path = os.path.expanduser('~/.jera/config')
            
            # Carrega configuração existente ou cria uma nova
            config_data = {}
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config_data = yaml.safe_load(f) or {}
            
            # Atualiza a configuração com o cluster atual
            config_data['current_cluster'] = {
                'name': selected_cluster,
                'region': region,
                'profile': selected_profile
            }
            
            # Salva a configuração
            with open(config_path, 'w') as f:
                yaml.dump(config_data, f)
            
            console.print(f"✅ Configuração do kubectl atualizada com sucesso para o cluster '{selected_cluster}'!", style="bold green")
        except subprocess.CalledProcessError as e:
            console.print(f"❌ Erro ao atualizar kubeconfig: {str(e)}", style="bold red")
            
    except subprocess.CalledProcessError as e:
        console.print(f"❌ Erro durante a inicialização: {str(e)}", style="bold red")

@click.command()
@click.argument('namespace', required=False)
def use(namespace=None):
    """Seleciona o namespace atual para operações."""
    try:
        config.load_kube_config()
        v1 = client.CoreV1Api()
        available_namespaces = [ns.metadata.name for ns in v1.list_namespace().items]
        
        if not available_namespaces:
            console.print("❌ Nenhum namespace encontrado no cluster.", style="bold red")
            return
            
        selected_namespace = namespace
        
        # Se não foi fornecido um namespace, mostra a lista interativa
        if not selected_namespace:
            # Ordena os namespaces alfabeticamente para facilitar a busca
            available_namespaces.sort()
            
            questions = [
                inquirer.List('namespace',
                             message="Selecione o namespace para usar",
                             choices=available_namespaces,
                             )
            ]
            answers = inquirer.prompt(questions)
            
            if answers:
                selected_namespace = answers['namespace']
            else:
                return
        
        # Verifica se o namespace existe
        if selected_namespace not in available_namespaces:
            console.print(f"❌ Namespace '{selected_namespace}' não encontrado!", style="bold red")
            return
            
        # Salva o namespace selecionado
        os.makedirs(os.path.expanduser('~/.jera'), exist_ok=True)
        config_path = os.path.expanduser('~/.jera/config')
        
        # Carrega configuração existente ou cria uma nova
        config_data = {}
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f) or {}
        
        # Atualiza apenas o namespace, mantendo o resto da configuração
        config_data['namespace'] = selected_namespace
        
        # Salva a configuração
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)
            
        console.print(f"✅ Namespace alterado para: [bold green]{selected_namespace}[/]", style="bold")
    except Exception as e:
        console.print(f"❌ Erro ao alterar namespace: {str(e)}", style="bold red")

@click.command(name="use-cluster")
@click.argument('cluster_name', required=False)
@click.option('--region', '-r', default='us-east-1', help='Região AWS onde o cluster está localizado')
@click.option('--profile', '-p', help='Profile AWS para usar')
def use_cluster(cluster_name=None, region='us-east-1', profile=None):
    """Alterna entre diferentes clusters Kubernetes."""
    try:
        # Verifica se tem uma sessão AWS ativa
        if not check_aws_sso_session():
            console.print("\n⚠️  Você não tem uma sessão AWS SSO ativa!", style="bold yellow")
            console.print("\n📝 Use o comando 'jeracli login-aws' para fazer login primeiro.", style="bold blue")
            return
        
        # Lista os profiles disponíveis
        result = subprocess.run(
            ["aws", "configure", "list-profiles"],
            capture_output=True,
            text=True
        )
        profiles = result.stdout.strip().split('\n')
        
        # Carrega a configuração atual
        config_path = os.path.expanduser('~/.jera/config')
        config_data = {}
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f) or {}
        
        current_profile = profile
        
        # Se não foi fornecido um profile, mostra a lista interativa
        if not current_profile:
            # Obtém o profile atual da configuração (se existir)
            current_profile_from_config = None
            if 'current_cluster' in config_data and 'profile' in config_data['current_cluster']:
                current_profile_from_config = config_data['current_cluster']['profile']
            
            # Prepara as opções com o perfil atual destacado
            profile_choices = []
            for p in profiles:
                if p == current_profile_from_config:
                    profile_choices.append(f"{p} (atual)")
                else:
                    profile_choices.append(p)
            
            questions = [
                inquirer.List('profile',
                            message="Selecione o profile AWS para usar",
                            choices=profile_choices,
                            )
            ]
            answers = inquirer.prompt(questions)
            
            if answers:
                # Remove o sufixo " (atual)" se presente
                current_profile = answers['profile'].replace(" (atual)", "")
            else:
                return
        
        # Lista os clusters disponíveis para o profile selecionado
        console.print(f"🔍 Listando clusters EKS disponíveis com profile '{current_profile}'...", style="bold blue")
        
        try:
            result = subprocess.run(
                ["aws", "eks", "list-clusters", "--region", region, "--profile", current_profile],
                capture_output=True,
                text=True,
                check=True
            )
            clusters_data = json.loads(result.stdout)
            available_clusters = clusters_data.get("clusters", [])
            
            if not available_clusters:
                console.print(f"❌ Nenhum cluster EKS encontrado na conta com profile '{current_profile}'.", style="bold red")
                return
            
            selected_cluster = cluster_name
            
            # Se não foi fornecido um cluster, mostra a lista interativa
            if not selected_cluster:
                # Obtém o cluster atual da configuração (se existir)
                current_cluster = None
                if 'current_cluster' in config_data and 'name' in config_data['current_cluster']:
                    current_cluster = config_data['current_cluster']['name']
                
                # Prepara as opções com o cluster atual destacado
                cluster_choices = []
                for c in available_clusters:
                    if c == current_cluster:
                        cluster_choices.append(f"{c} (atual)")
                    else:
                        cluster_choices.append(c)
                
                questions = [
                    inquirer.List('cluster',
                                message="Selecione um cluster EKS para usar",
                                choices=cluster_choices,
                                )
                ]
                answers = inquirer.prompt(questions)
                
                if answers:
                    # Remove o sufixo " (atual)" se presente
                    selected_cluster = answers['cluster'].replace(" (atual)", "")
                else:
                    return
            
            # Verifica se o cluster selecionado existe
            if selected_cluster not in available_clusters:
                console.print(f"❌ Cluster '{selected_cluster}' não encontrado na conta.", style="bold red")
                return
            
            # Atualiza o kubeconfig para o cluster selecionado
            console.print(f"🔄 Atualizando kubeconfig para o cluster '{selected_cluster}'...", style="bold blue")
            subprocess.run([
                "aws", "eks", "update-kubeconfig",
                "--name", selected_cluster,
                "--region", region,
                "--profile", current_profile
            ], check=True)
            
            # Atualiza a configuração do Jera CLI
            config_data['current_cluster'] = {
                'name': selected_cluster,
                'region': region,
                'profile': current_profile
            }
            
            # Salva a configuração
            os.makedirs(os.path.expanduser('~/.jera'), exist_ok=True)
            with open(config_path, 'w') as f:
                yaml.dump(config_data, f)
            
            console.print(f"✅ Cluster alterado para: [bold green]{selected_cluster}[/] com profile [bold green]{current_profile}[/]", style="bold")
            
            # Lista os clusters configurados após a alteração
            list_configured_clusters()
            
        except Exception as e:
            console.print(f"❌ Erro ao listar ou selecionar clusters: {str(e)}", style="bold red")
            
    except Exception as e:
        console.print(f"❌ Erro ao alternar entre clusters: {str(e)}", style="bold red")

def list_configured_clusters():
    """Lista todos os contextos de clusters configurados no kubeconfig."""
    try:
        # Obtém os contextos do kubeconfig
        result = subprocess.run(
            ["kubectl", "config", "get-contexts"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            console.print("❌ Erro ao listar contextos do kubectl.", style="bold red")
            return
        
        # Obtém o contexto atual
        current_context_result = subprocess.run(
            ["kubectl", "config", "current-context"],
            capture_output=True,
            text=True
        )
        current_context = current_context_result.stdout.strip() if current_context_result.returncode == 0 else None
        
        # Cria uma tabela com os contextos
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Nome do Contexto")
        table.add_column("Cluster")
        table.add_column("Usuário")
        table.add_column("Status")
        
        # Parse das linhas do resultado
        lines = result.stdout.strip().split('\n')
        if len(lines) > 1:  # Ignora o cabeçalho
            for line in lines[1:]:  # Pula o cabeçalho
                parts = line.strip().split()
                if len(parts) >= 3:
                    is_current = '*' in parts[0]
                    
                    # Ajusta os índices baseados se tem o asterisco no começo
                    if is_current:
                        context_name = parts[1]
                        cluster_name = parts[2]
                        user_name = parts[3] if len(parts) > 3 else "N/A"
                    else:
                        context_name = parts[0]
                        cluster_name = parts[1]
                        user_name = parts[2] if len(parts) > 2 else "N/A"
                    
                    status = "[bold green]ATUAL[/]" if context_name == current_context else ""
                    
                    table.add_row(
                        context_name,
                        cluster_name,
                        user_name,
                        status
                    )
        
        console.print("\n📋 Clusters configurados:", style="bold blue")
        console.print(table)
        console.print("\nDica: Use 'jeracli use-cluster' para alternar entre clusters.", style="dim")
        
    except Exception as e:
        console.print(f"❌ Erro ao listar clusters configurados: {str(e)}", style="bold red")

@click.command(name="login-aws")
def login_aws():
    """Faz login no AWS SSO de forma interativa."""
    try:
        # Verifica se o AWS CLI está instalado
        try:
            result = subprocess.run(["aws", "--version"], capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception("AWS CLI não encontrado")
        except:
            console.print("\n❌ AWS CLI não está instalado!", style="bold red")
            console.print("\n📝 Para instalar o AWS CLI:", style="bold yellow")
            console.print("1. Linux/MacOS:", style="dim")
            console.print("   https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html")
            console.print("\n2. Windows:", style="dim")
            console.print("   https://aws.amazon.com/cli/")
            console.print("\nInstale o AWS CLI e tente novamente.", style="bold yellow")
            return

        # Verifica se já existe configuração do SSO
        if not check_aws_sso_config():
            console.print("\n📝 Configurando AWS SSO pela primeira vez...", style="bold blue")
            
            # Configura o SSO com valores padrão da Jera
            questions = [
                inquirer.Text('profile',
                            message="Digite o nome do seu profile (ex: seu-nome)",
                            validate=lambda _, x: len(x) >= 2)
            ]
            answers = inquirer.prompt(questions)
            
            if not answers:
                return
                
            profile = answers['profile']
            
            # Cria o diretório .aws se não existir
            aws_dir = os.path.expanduser("~/.aws")
            os.makedirs(aws_dir, exist_ok=True)
            
            # Cria/atualiza a configuração
            config_file = os.path.join(aws_dir, "config")
            with open(config_file, 'a') as f:
                f.write(f"\n[profile {profile}]\n")
                f.write("sso_start_url = https://jera.awsapps.com/start\n")
                f.write("sso_region = us-east-1\n")
                f.write("sso_account_id = ACCOUNT_ID\n")  # Substitua pelo ID da conta
                f.write("sso_role_name = AdministratorAccess\n")
                f.write("region = us-east-1\n")
                f.write("output = json\n")
            
            console.print(f"\n✅ Profile [bold green]{profile}[/] configurado!", style="bold")
            
            # Faz o login
            console.print("\n🔑 Iniciando login no AWS SSO...", style="bold blue")
            subprocess.run(["aws", "sso", "login", "--profile", profile])
            
        else:
            # Lista os profiles disponíveis
            result = subprocess.run(
                ["aws", "configure", "list-profiles"],
                capture_output=True,
                text=True
            )
            profiles = result.stdout.strip().split('\n')
            
            # Permite selecionar o profile
            questions = [
                inquirer.List('profile',
                             message="Selecione o profile para login",
                             choices=profiles,
                             )
            ]
            answers = inquirer.prompt(questions)
            
            if answers:
                profile = answers['profile']
                console.print(f"\n🔑 Fazendo login com o profile [bold green]{profile}[/]...", style="bold blue")
                subprocess.run(["aws", "sso", "login", "--profile", profile])
            
        console.print("\n✅ Login realizado com sucesso!", style="bold green")
        
    except Exception as e:
        console.print(f"\n❌ Erro ao fazer login: {str(e)}", style="bold red")
        if "The SSO session has expired" in str(e):
            console.print("A sessão SSO expirou. Tente novamente.", style="yellow")

@click.command(name="clusters")
def clusters():
    """Lista todos os clusters Kubernetes configurados."""
    list_configured_clusters() 
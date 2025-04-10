import click
from rich.console import Console
from rich.table import Table
import subprocess
import json
import yaml
import os
import inquirer
from kubernetes import client, config
from ..utils.kubernetes import check_aws_sso_config, check_aws_sso_session, check_azure_cli_installed, check_azure_session, get_azure_subscriptions, get_azure_current_subscription, set_azure_subscription, get_azure_clusters, get_aks_credentials
from ..utils.common import load_namespace
console = Console()

def load_namespace():
    """Carrega o namespace salvo na configuração"""
    config_path = os.path.expanduser('~/.jera/config')
    if os.path.exists(config_path):
        with open(config_path) as f:
            config_data = yaml.safe_load(f) or {}
            return config_data.get('namespace')
    return None

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
        
        # Adiciona a opção para criar um novo profile
        profiles.append("+ Adicionar novo profile")
        
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
                
                # Se a opção de adicionar novo profile foi selecionada
                if selected_profile == "+ Adicionar novo profile":
                    console.print("\n📝 Iniciando configuração AWS SSO. Siga os passos abaixo:", style="bold blue")
                    console.print("   - SSO start URL: https://jera.awsapps.com/start", style="dim white")
                    console.print("   - SSO Region: us-east-1", style="dim white")
                    console.print("   - CLI default client Region: us-east-1", style="dim white")
                    console.print("   - CLI default output format: json", style="dim white")
                    console.print("   - CLI profile name: nome-do-seu-perfil", style="dim white")
                    
                    # Executa o comando tradicional para configurar o SSO
                    console.print("\n🔧 Executando configuração AWS SSO interativa...", style="bold blue")
                    try:
                        # Salva a lista atual de profiles antes da configuração
                        before_profiles = set(profiles) - set(["+ Adicionar novo profile"])
                        
                        # Usa subprocess.run para garantir que o terminal permaneça interativo
                        subprocess.run(["aws", "configure", "sso"], check=True)
                        
                        # Atualiza a lista de profiles
                        profile_result = subprocess.run(
                            ["aws", "configure", "list-profiles"],
                            capture_output=True,
                            text=True,
                            check=True
                        )
                        new_profiles = profile_result.stdout.strip().split('\n')
                        after_profiles = set(new_profiles)
                        
                        # Identifica os profiles adicionados
                        added_profiles = after_profiles - before_profiles
                        
                        # Mostra a lista atualizada para seleção
                        if added_profiles:
                            console.print(f"\n✅ Novo(s) profile(s) configurado(s) com sucesso: {', '.join(added_profiles)}", style="bold green")
                            questions = [
                                inquirer.List('profile',
                                            message="Selecione o profile para usar",
                                            choices=new_profiles,
                                            )
                            ]
                            answers = inquirer.prompt(questions)
                            
                            if answers:
                                selected_profile = answers['profile']
                            else:
                                return
                        else:
                            # Mesmo que não tenha detectado novos profiles, permite selecionar um dos existentes
                            console.print("\n⚠️ Não foi possível detectar novos profiles, mas a configuração pode ter sido realizada.", style="bold yellow")
                            console.print("Por favor, selecione um profile existente para continuar:", style="bold blue")
                            
                            questions = [
                                inquirer.List('profile',
                                            message="Selecione o profile para usar",
                                            choices=new_profiles,
                                            )
                            ]
                            answers = inquirer.prompt(questions)
                            
                            if answers:
                                selected_profile = answers['profile']
                            else:
                                return
                    except subprocess.CalledProcessError:
                        console.print(f"❌ Erro ao configurar o profile AWS SSO.", style="bold red")
                        return
            else:
                return
        
        # Faz login se necessário
        if not check_aws_sso_session():
            console.print(f"\n🔑 Fazendo login com o profile [bold green]{selected_profile}[/]...", style="bold blue")
            
            # Usa subprocess.run sem capturar a saída para manter o terminal interativo
            subprocess.run(
                ["aws", "sso", "login", "--profile", selected_profile],
                check=False  # Não lança exceção em caso de erro
            )
            
            # Verifica se o login foi bem-sucedido
            verify_result = subprocess.run(
                ["aws", "sts", "get-caller-identity", "--profile", selected_profile],
                capture_output=True,
                text=True,
                check=False
            )
            
            if verify_result.returncode != 0:
                console.print(f"❌ Erro ao fazer login com o profile '{selected_profile}'", style="bold red")
                return
        
        # Se não foi fornecido cluster, lista os clusters disponíveis
        selected_cluster = cluster
        if not selected_cluster:
            console.print(f"🔍 Listando clusters EKS disponíveis com profile '{selected_profile}'...", style="bold blue")
            
            try:
                # Primeiro verifica se o usuário tem permissão para listar clusters do EKS
                test_cmd = [
                    "aws", "sts", "get-caller-identity",
                    "--profile", selected_profile,
                    "--region", region
                ]
                test_result = subprocess.run(
                    test_cmd,
                    capture_output=True,
                    text=True
                )
                
                if test_result.returncode != 0:
                    console.print(f"❌ Erro de autenticação com o profile '{selected_profile}'", style="bold red")
                    console.print("\n📝 Possíveis soluções:", style="bold yellow")
                    console.print("1. Verifique se a sessão SSO está ativa:", style="dim white")
                    console.print(f"   aws sso login --profile {selected_profile}", style="bold green")
                    console.print("2. Verifique se o profile tem as permissões necessárias para acessar o EKS", style="dim white")
                    console.print("3. Tente usar outro profile com permissões adequadas", style="dim white")
                    return
                
                result = subprocess.run(
                    ["aws", "eks", "list-clusters", "--region", region, "--profile", selected_profile],
                    capture_output=True,
                    text=True,
                    check=False  # Não lança exceção em caso de erro
                )
                
                if result.returncode != 0:
                    error_message = result.stderr.strip()
                    console.print(f"❌ Erro ao listar clusters EKS:", style="bold red")
                    
                    if "AccessDeniedException" in error_message or "UnauthorizedException" in error_message:
                        console.print("\n⚠️ O profile não tem permissão para listar clusters do EKS.", style="bold yellow")
                        console.print(f"\n📝 Tente logar novamente com o profile '{selected_profile}':", style="bold blue")
                        console.print(f"   aws sso login --profile {selected_profile}", style="bold green")
                        console.print("\nOu forneça o nome do cluster diretamente:", style="bold blue")
                        console.print(f"   jeracli init -c nome-do-cluster -p {selected_profile}", style="bold green")
                    elif "ExpiredToken" in error_message:
                        console.print("\n⚠️ Token de acesso AWS expirado.", style="bold yellow")
                        console.print(f"\n📝 Renove sua sessão:", style="bold blue")
                        console.print(f"   aws sso login --profile {selected_profile}", style="bold green")
                    else:
                        console.print(f"\nErro detalhado: {error_message}", style="dim red")
                        console.print("\n📝 Se você conhece o nome do cluster, pode fornecê-lo diretamente:", style="bold blue")
                        console.print(f"   jeracli init -c nome-do-cluster -p {selected_profile}", style="bold green")
                    
                    # Questiona o usuário se deseja informar o nome do cluster manualmente
                    manual_cluster = click.prompt("Deseja informar o nome do cluster manualmente? [s/N]", default="n")
                    if manual_cluster.lower() == "s":
                        selected_cluster = click.prompt("Digite o nome do cluster")
                    else:
                        return
                else:
                    try:
                        clusters_data = json.loads(result.stdout)
                        available_clusters = clusters_data.get("clusters", [])
                        
                        if not available_clusters:
                            console.print("❌ Nenhum cluster EKS encontrado na conta.", style="bold red")
                            
                            # Questiona o usuário se deseja informar o nome do cluster manualmente
                            manual_cluster = click.prompt("Deseja informar o nome do cluster manualmente? [s/N]", default="n")
                            if manual_cluster.lower() == "s":
                                selected_cluster = click.prompt("Digite o nome do cluster")
                            else:
                                return
                        else:
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
                    except json.JSONDecodeError:
                        console.print("❌ Erro ao processar a resposta da AWS.", style="bold red")
                        console.print(f"Resposta recebida: {result.stdout}", style="dim")
                        
                        # Questiona o usuário se deseja informar o nome do cluster manualmente
                        manual_cluster = click.prompt("Deseja informar o nome do cluster manualmente? [s/N]", default="n")
                        if manual_cluster.lower() == "s":
                            selected_cluster = click.prompt("Digite o nome do cluster")
                            return
                        else:
                            return
            except Exception as e:
                console.print(f"❌ Erro ao listar clusters: {str(e)}", style="bold red")
                console.print("\n📝 Se você conhece o nome do cluster, pode fornecê-lo diretamente:", style="bold blue")
                console.print(f"   jeracli init -c nome-do-cluster -p {selected_profile}", style="bold green")
                
                # Questiona o usuário se deseja informar o nome do cluster manualmente
                manual_cluster = click.prompt("Deseja informar o nome do cluster manualmente? [s/N]", default="n")
                if manual_cluster.lower() == "s":
                    selected_cluster = click.prompt("Digite o nome do cluster")
                    return
                else:
                    return
        
        if not selected_cluster:
            console.print("❌ Nome do cluster não informado.", style="bold red")
            return
        
        # Tenta usar o profile para atualizar o kubeconfig
        console.print(f"🔄 Atualizando kubeconfig para o cluster '{selected_cluster}' com profile '{selected_profile}'...", style="bold blue")
        try:
            update_result = subprocess.run([
                "aws", "eks", "update-kubeconfig",
                "--name", selected_cluster,
                "--region", region,
                "--profile", selected_profile
            ], capture_output=True, text=True, check=False)
            
            if update_result.returncode != 0:
                error_message = update_result.stderr.strip()
                console.print(f"❌ Erro ao atualizar kubeconfig:", style="bold red")
                
                if "ResourceNotFoundException" in error_message:
                    console.print(f"\n⚠️ Cluster '{selected_cluster}' não encontrado na conta com o profile '{selected_profile}'.", style="bold yellow")
                    console.print("\n📝 Verifique se o nome do cluster está correto e se o profile tem acesso a ele.", style="bold blue")
                elif "AccessDeniedException" in error_message or "UnauthorizedException" in error_message:
                    console.print("\n⚠️ O profile não tem permissão para acessar este cluster do EKS.", style="bold yellow")
                    console.print(f"\n📝 Tente logar novamente com o profile '{selected_profile}':", style="bold blue")
                    console.print(f"   aws sso login --profile {selected_profile}", style="bold green")
                elif "ExpiredToken" in error_message:
                    console.print("\n⚠️ Token de acesso AWS expirado.", style="bold yellow")
                    console.print(f"\n📝 Renove sua sessão:", style="bold blue")
                    console.print(f"   aws sso login --profile {selected_profile}", style="bold green")
                else:
                    console.print(f"\nErro detalhado: {error_message}", style="dim red")
                return
            
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
            
            # Testa a conexão com o cluster
            test_cluster = subprocess.run(
                ["kubectl", "get", "nodes", "--request-timeout=5s"],
                capture_output=True,
                text=True,
                check=False
            )
            
            if test_cluster.returncode != 0:
                console.print("\n⚠️ A configuração foi atualizada, mas não foi possível conectar ao cluster.", style="bold yellow")
                console.print("📝 Isso pode ocorrer por:", style="bold blue")
                console.print("  • Problemas de conectividade de rede", style="dim white")
                console.print("  • Problemas de autenticação", style="dim white")
                console.print("  • Configurações adicionais podem ser necessárias", style="dim white")
                console.print("\nTente usar o seguinte comando para verificar a conexão:", style="bold blue")
                console.print("  kubectl get nodes", style="bold green")
            else:
                console.print("\n✅ Conexão com o cluster estabelecida com sucesso!", style="bold green")
        except Exception as e:
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
@click.option('--azure', '-az', is_flag=True, help='Indica que o cluster está no Azure')
@click.option('--aws', is_flag=True, help='Indica que o cluster está na AWS')
@click.option('--switch', '-s', is_flag=True, help='Alterna entre AWS e Azure')
@click.option('--resource-group', '-g', help='Grupo de recursos do cluster AKS (apenas para Azure)')
@click.option('--subscription', '--sub', help='Assinatura Azure para usar (apenas para Azure)')
def use_cluster(cluster_name=None, region='us-east-1', profile=None, azure=False, aws=False, switch=False, resource_group=None, subscription=None):
    """Alterna entre diferentes clusters Kubernetes."""
    try:
        # Carrega a configuração atual
        config_path = os.path.expanduser('~/.jera/config')
        config_data = {}
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f) or {}
        
        # Verifica o tipo atual de cluster configurado (aws ou azure)
        current_type = config_data.get('current_type', 'aws')
        
        # Se a flag de troca está ativa, inverte o tipo atual
        if switch:
            is_azure = current_type != 'azure'  # Inverte o tipo atual
            console.print(f"\n🔄 Alternando para {'Azure AKS' if is_azure else 'AWS EKS'}...", style="bold blue")
        else:
            # Senão, usa as flags ou mantém o tipo atual
            if aws and azure:
                console.print("❌ Não é possível usar as flags --aws e --azure ao mesmo tempo.", style="bold red")
                return
            elif aws:
                is_azure = False
            elif azure:
                is_azure = True
            else:
                is_azure = current_type == 'azure'
                
        # Redireciona para o handler específico com base no tipo
        if is_azure:
            return use_cluster_azure(cluster_name, resource_group, subscription, config_data, config_path)
        else:
            return use_cluster_aws(cluster_name, region, profile, config_data, config_path)
    except Exception as e:
        console.print(f"❌ Erro ao alternar entre clusters: {str(e)}", style="bold red")

def use_cluster_aws(cluster_name=None, region='us-east-1', profile=None, config_data=None, config_path=None):
    """Alterna para um cluster AWS EKS."""
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
        
        profile = profile
        
        # Se não foi fornecido um profile, mostra a lista interativa
        if not profile:
            # Obtém o profile atual da configuração (se existir)
            profile_from_config = None
            if 'current_cluster' in config_data and 'profile' in config_data['current_cluster']:
                profile_from_config = config_data['current_cluster']['profile']
            
            # Prepara as opções com o perfil atual destacado
            profile_choices = []
            for p in profiles:
                if p == profile_from_config:
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
                profile = answers['profile'].replace(" (atual)", "")
            else:
                return
        
        # Lista os clusters disponíveis para o profile selecionado
        console.print(f"🔍 Listando clusters EKS disponíveis com profile '{profile}'...", style="bold blue")
        
        try:
            # Primeiro verifica se o usuário tem permissão para listar clusters do EKS
            test_cmd = [
                "aws", "sts", "get-caller-identity",
                "--profile", profile,
                "--region", region
            ]
            test_result = subprocess.run(
                test_cmd,
                capture_output=True,
                text=True
            )
            
            if test_result.returncode != 0:
                console.print(f"❌ Erro de autenticação com o profile '{profile}'", style="bold red")
                console.print("\n📝 Possíveis soluções:", style="bold yellow")
                console.print("1. Verifique se a sessão SSO está ativa:", style="dim white")
                console.print(f"   aws sso login --profile {profile}", style="bold green")
                console.print("2. Verifique se o profile tem as permissões necessárias para acessar o EKS", style="dim white")
                console.print("3. Tente usar outro profile com permissões adequadas", style="dim white")
                return

            result = subprocess.run(
                ["aws", "eks", "list-clusters", "--region", region, "--profile", profile],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                error_message = result.stderr.strip()
                console.print(f"❌ Erro ao listar clusters EKS:", style="bold red")
                
                if "AccessDeniedException" in error_message or "UnauthorizedException" in error_message:
                    console.print("\n⚠️ O profile não tem permissão para listar clusters do EKS.", style="bold yellow")
                    console.print(f"\n📝 Tente logar novamente com o profile '{profile}':", style="bold blue")
                    console.print(f"   aws sso login --profile {profile}", style="bold green")
                    console.print("\nOu forneça o nome do cluster diretamente:", style="bold blue")
                    console.print(f"   jeracli use-cluster nome-do-cluster -p {profile}", style="bold green")
                elif "ExpiredToken" in error_message:
                    console.print("\n⚠️ Token de acesso AWS expirado.", style="bold yellow")
                    console.print(f"\n📝 Renove sua sessão:", style="bold blue")
                    console.print(f"   aws sso login --profile {profile}", style="bold green")
                else:
                    console.print(f"\nErro detalhado: {error_message}", style="dim red")
                    console.print("\n📝 Se você conhece o nome do cluster, pode fornecê-lo diretamente:", style="bold blue")
                    console.print(f"   jeracli use-cluster nome-do-cluster -p {profile}", style="bold green")
                
                # Questiona o usuário se deseja informar o nome do cluster manualmente
                manual_cluster = click.prompt("Deseja informar o nome do cluster manualmente? [s/N]", default="n")
                if manual_cluster.lower() == "s":
                    selected_cluster = click.prompt("Digite o nome do cluster")
                    # Define o argumento cluster_name para usar no restante do código
                    cluster_name = selected_cluster
                else:
                    return
            else:
                try:
                    clusters_data = json.loads(result.stdout)
                    available_clusters = clusters_data.get("clusters", [])
                    
                    if not available_clusters:
                        console.print(f"❌ Nenhum cluster EKS encontrado na conta com profile '{profile}'.", style="bold red")
                        
                        # Questiona o usuário se deseja informar o nome do cluster manualmente
                        manual_cluster = click.prompt("Deseja informar o nome do cluster manualmente? [s/N]", default="n")
                        if manual_cluster.lower() == "s":
                            selected_cluster = click.prompt("Digite o nome do cluster")
                            # Define o argumento cluster_name para usar no restante do código
                            cluster_name = selected_cluster
                        else:
                            return
                    else:
                        # Se um nome de cluster foi fornecido, verifica se ele existe na lista
                        if cluster_name and cluster_name not in available_clusters:
                            console.print(f"⚠️ Cluster '{cluster_name}' não encontrado na lista. Verifique o nome e tente novamente.", style="bold yellow")
                            
                            # Questiona se deseja selecionar entre os clusters disponíveis
                            select_from_list = click.prompt("Deseja selecionar entre os clusters disponíveis? [S/n]", default="s")
                            if select_from_list.lower() != "s":
                                return
                            
                            # Reseta o argumento para forçar seleção interativa
                            cluster_name = None
                        
                        # Se não foi fornecido um cluster ou o nome não foi encontrado, mostra a lista interativa
                        if not cluster_name:
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
                                # Define o argumento cluster_name para usar no restante do código
                                cluster_name = selected_cluster
                            else:
                                return
                except json.JSONDecodeError:
                    console.print("❌ Erro ao processar a resposta da AWS.", style="bold red")
                    console.print(f"Resposta recebida: {result.stdout}", style="dim")
                    
                    # Questiona o usuário se deseja informar o nome do cluster manualmente
                    manual_cluster = click.prompt("Deseja informar o nome do cluster manualmente? [s/N]", default="n")
                    if manual_cluster.lower() == "s":
                        selected_cluster = click.prompt("Digite o nome do cluster")
                        # Define o argumento cluster_name para usar no restante do código
                        cluster_name = selected_cluster
                    else:
                        return
        except Exception as e:
            console.print(f"❌ Erro ao listar ou selecionar clusters: {str(e)}", style="bold red")
            console.print("\n📝 Se você conhece o nome do cluster, pode fornecê-lo diretamente:", style="bold blue")
            console.print(f"   jeracli use-cluster nome-do-cluster -p {profile}", style="bold green")
            
            # Questiona o usuário se deseja informar o nome do cluster manualmente
            manual_cluster = click.prompt("Deseja informar o nome do cluster manualmente? [s/N]", default="n")
            if manual_cluster.lower() == "s":
                selected_cluster = click.prompt("Digite o nome do cluster")
                # Define o argumento cluster_name para usar no restante do código
                cluster_name = selected_cluster
            else:
                return
        
        # Faz login se necessário
        if not check_aws_sso_session():
            console.print(f"\n🔑 Fazendo login com o profile [bold green]{profile}[/]...", style="bold blue")
            
            # Usa subprocess.run sem capturar a saída para manter o terminal interativo
            subprocess.run(
                ["aws", "sso", "login", "--profile", profile],
                check=False  # Não lança exceção em caso de erro
            )
            
            # Verifica se o login foi bem-sucedido
            verify_result = subprocess.run(
                ["aws", "sts", "get-caller-identity", "--profile", profile],
                capture_output=True,
                text=True,
                check=False
            )
            
            if verify_result.returncode != 0:
                console.print(f"❌ Erro ao fazer login com o profile '{profile}'", style="bold red")
                return
        
        # Continua apenas se temos um nome de cluster válido
        if not cluster_name:
            console.print("❌ Nome do cluster não informado.", style="bold red")
            return
        
        # Atualiza o kubeconfig para o cluster selecionado
        console.print(f"🔄 Atualizando kubeconfig para o cluster '{cluster_name}'...", style="bold blue")
        
        try:
            update_result = subprocess.run([
                "aws", "eks", "update-kubeconfig",
                "--name", cluster_name,
                "--region", region,
                "--profile", profile
            ], capture_output=True, text=True, check=False)
            
            if update_result.returncode != 0:
                error_message = update_result.stderr.strip()
                console.print(f"❌ Erro ao atualizar kubeconfig:", style="bold red")
                
                if "ResourceNotFoundException" in error_message:
                    console.print(f"\n⚠️ Cluster '{cluster_name}' não encontrado na conta com o profile '{profile}'.", style="bold yellow")
                    console.print("\n📝 Verifique se o nome do cluster está correto e se o profile tem acesso a ele.", style="bold blue")
                elif "AccessDeniedException" in error_message or "UnauthorizedException" in error_message:
                    console.print("\n⚠️ O profile não tem permissão para acessar este cluster do EKS.", style="bold yellow")
                    console.print(f"\n📝 Tente logar novamente com o profile '{profile}':", style="bold blue")
                    console.print(f"   aws sso login --profile {profile}", style="bold green")
                elif "ExpiredToken" in error_message:
                    console.print("\n⚠️ Token de acesso AWS expirado.", style="bold yellow")
                    console.print(f"\n📝 Renove sua sessão:", style="bold blue")
                    console.print(f"   aws sso login --profile {profile}", style="bold green")
                else:
                    console.print(f"\nErro detalhado: {error_message}", style="dim red")
                return
                
            # Atualiza a configuração do Jera CLI
            config_data['current_cluster'] = {
                'name': cluster_name,
                'region': region,
                'profile': profile
            }
            config_data['current_type'] = 'aws'
            
            # Salva a configuração
            os.makedirs(os.path.expanduser('~/.jera'), exist_ok=True)
            with open(config_path, 'w') as f:
                yaml.dump(config_data, f)
            
            console.print(f"✅ Cluster alterado para: [bold green]{cluster_name}[/] com profile [bold green]{profile}[/]", style="bold")
            
            # Testa a conexão com o cluster
            test_cluster = subprocess.run(
                ["kubectl", "get", "nodes", "--request-timeout=5s"],
                capture_output=True,
                text=True,
                check=False
            )
            
            if test_cluster.returncode != 0:
                console.print("\n⚠️ A configuração foi atualizada, mas não foi possível conectar ao cluster.", style="bold yellow")
                console.print("📝 Isso pode ocorrer por:", style="bold blue")
                console.print("  • Problemas de conectividade de rede", style="dim white")
                console.print("  • Problemas de autenticação", style="dim white")
                console.print("  • Configurações adicionais podem ser necessárias", style="dim white")
                console.print("\nTente usar o seguinte comando para verificar a conexão:", style="bold blue")
                console.print("  kubectl get nodes", style="bold green")
            else:
                console.print("\n✅ Conexão com o cluster estabelecida com sucesso!", style="bold green")
            
            # Lista os clusters configurados após a alteração
            list_configured_clusters()
        except Exception as e:
            console.print(f"❌ Erro ao alternar para o cluster: {str(e)}", style="bold red")
    except Exception as e:
        console.print(f"❌ Erro ao alternar para o cluster AWS: {str(e)}", style="bold red")
    
def use_cluster_azure(cluster_name=None, resource_group=None, subscription=None, config_data=None, config_path=None):
    """Alterna para um cluster Azure AKS."""
    try:
        # Verifica se o Azure CLI está instalado
        if not check_azure_cli_installed():
            console.print("\n❌ Azure CLI não está instalado!", style="bold red")
            console.print("\n📝 Para instalar o Azure CLI:", style="bold yellow")
            console.print("1. Linux/MacOS:", style="dim")
            console.print("   curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash", style="bold green")
            console.print("\n2. Windows:", style="dim")
            console.print("   https://docs.microsoft.com/pt-br/cli/azure/install-azure-cli-windows", style="bold green")
            console.print("\nInstale o Azure CLI e tente novamente.", style="bold yellow")
            return
        
        # Verifica se tem uma sessão Azure ativa
        if not check_azure_session():
            console.print("\n⚠️  Você não tem uma sessão Azure ativa!", style="bold yellow")
            console.print("\n📝 Use o comando 'jeracli login-azure' para fazer login primeiro.", style="bold blue")
            return

        # Verifica a assinatura atual
        current_subscription = get_azure_current_subscription()
        selected_subscription = subscription or current_subscription
        
        if subscription and subscription != current_subscription:
            console.print(f"\n🔄 Mudando para a assinatura [bold blue]{selected_subscription}[/]...", style="bold blue")
            
            if not set_azure_subscription(selected_subscription):
                console.print(f"❌ Erro ao alterar a assinatura.", style="bold red")
                return
        
        # Se não foi fornecido um cluster, lista os clusters disponíveis
        selected_cluster = cluster
        selected_resource_group = resource_group
        
        if not selected_cluster:
            console.print(f"\n🔍 Listando clusters AKS na assinatura [bold blue]{selected_subscription}[/]...", style="bold blue")
            
            try:
                # Obtém todos os clusters com seus respectivos grupos de recursos
                result = subprocess.run(
                    ["az", "aks", "list", "--query", "[].{name:name, resourceGroup:resourceGroup}", "-o", "json"],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    console.print(f"❌ Erro ao listar clusters AKS: {result.stderr}", style="bold red")
                    return
                
                clusters = json.loads(result.stdout)
                
                if not clusters:
                    console.print("❌ Não foram encontrados clusters AKS nesta assinatura.", style="bold red")
                    return
                
                # Obtém o cluster atual da configuração (se existir)
                current_cluster = None
                current_resource_group = None
                
                if 'azure_cluster' in config_data:
                    current_cluster = config_data['azure_cluster']
                    current_resource_group = config_data.get('azure_resource_group')
                
                # Monta opções para o usuário selecionar
                cluster_choices = []
                for c in clusters:
                    cluster_info = f"{c['name']} (Grupo: {c['resourceGroup']})"
                    # Marca o cluster atual
                    if c['name'] == current_cluster and c['resourceGroup'] == current_resource_group:
                        cluster_choices.append(f"{cluster_info} (atual)")
                    else:
                        cluster_choices.append(cluster_info)
                
                questions = [
                    inquirer.List('cluster',
                                message="Selecione o cluster AKS",
                                choices=cluster_choices,
                                )
                ]
                answers = inquirer.prompt(questions)
                
                if not answers:
                    return
                
                # Extrai o nome do cluster e o grupo de recursos da seleção
                selected_option = answers['cluster'].replace(" (atual)", "")
                
                # Tenta encontrar o cluster e grupo de recursos correspondentes
                found = False
                for c in clusters:
                    if selected_option == f"{c['name']} (Grupo: {c['resourceGroup']})":
                        selected_cluster = c['name']
                        selected_resource_group = c['resourceGroup']
                        found = True
                        break
                
                # Se não encontrou na forma exata, tenta extrair o nome e grupo diretamente
                if not found:
                    # Tenta extrair o nome e o grupo da string selecionada
                    # Formato esperado: "nome-do-cluster (Grupo: nome-do-grupo)"
                    import re
                    match = re.match(r"([^(]+)\s*\(Grupo:\s*([^)]+)\)", selected_option)
                    if match:
                        selected_cluster = match.group(1).strip()
                        selected_resource_group = match.group(2).strip()
                    else:
                        console.print("❌ Não foi possível extrair o nome do cluster e grupo de recursos da seleção.", style="bold red")
                        return
                
            except Exception as e:
                console.print(f"❌ Erro ao listar clusters Azure: {str(e)}", style="bold red")
                return
        
        # Verifica se temos o grupo de recursos quando o cluster está definido
        if selected_cluster and not selected_resource_group:
            console.print("❌ Grupo de recursos não informado para o cluster Azure.", style="bold red")
            console.print("📝 Você precisa fornecer o grupo de recursos para clusters AKS:", style="bold blue")
            console.print(f"  jeracli use-cluster {selected_cluster} -az -g NOME_DO_GRUPO", style="bold green")
            return
        
        # Configura kubectl para o cluster selecionado
        console.print(f"\n🔄 Configurando kubectl para o cluster [bold green]{selected_cluster}[/]...", style="bold blue")
        
        success, stdout, stderr = get_aks_credentials(
            selected_cluster, 
            resource_group=selected_resource_group, 
            subscription=selected_subscription
        )
        
        if success:
            # Atualiza a configuração
            config_data['azure_cluster'] = selected_cluster
            config_data['azure_resource_group'] = selected_resource_group
            config_data['azure_subscription'] = selected_subscription
            config_data['current_type'] = 'azure'
            
            # Salva a configuração
            os.makedirs(os.path.expanduser('~/.jera'), exist_ok=True)
            with open(config_path, 'w') as f:
                yaml.dump(config_data, f)
            
            console.print(f"✅ Cluster alterado para: [bold green]{selected_cluster}[/] (Azure AKS)", style="bold")
            console.print(f"📊 Detalhes:", style="bold blue")
            console.print(f"   Cluster: {selected_cluster}", style="dim")
            console.print(f"   Grupo de recursos: {selected_resource_group}", style="dim")
            console.print(f"   Assinatura: {selected_subscription}", style="dim")
            
            # Testa a conexão com o cluster
            test_cluster = subprocess.run(
                ["kubectl", "get", "nodes", "--request-timeout=5s"],
                capture_output=True,
                text=True,
                check=False
            )
            
            if test_cluster.returncode != 0:
                console.print("\n⚠️ A configuração foi atualizada, mas não foi possível conectar ao cluster.", style="bold yellow")
                console.print("📝 Isso pode ocorrer por:", style="bold blue")
                console.print("  • Problemas de conectividade de rede", style="dim white")
                console.print("  • Problemas de autenticação", style="dim white")
                console.print("  • Configurações adicionais podem ser necessárias", style="dim white")
                console.print("\nTente usar o seguinte comando para verificar a conexão:", style="bold blue")
                console.print("  kubectl get nodes", style="bold green")
            else:
                console.print("\n✅ Conexão com o cluster estabelecida com sucesso!", style="bold green")
            
            # Lista os clusters configurados após a alteração
            list_configured_clusters()
        else:
            console.print(f"❌ Erro ao configurar o cluster: {stderr}", style="bold red")
            return
        
    except Exception as e:
        console.print(f"❌ Erro ao alternar para o cluster Azure: {str(e)}", style="bold red")

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
            console.print("   - SSO start URL: https://jera.awsapps.com/start", style="dim white")
            console.print("   - SSO Region: us-east-1", style="dim white")
            console.print("   - CLI default client Region: us-east-1", style="dim white")
            console.print("   - CLI default output format: json", style="dim white")
            console.print("   - CLI profile name: nome-do-seu-perfil", style="dim white")
            
            # Executa o comando tradicional para configurar o SSO
            console.print("\n🔧 Executando configuração AWS SSO interativa...", style="bold blue")
            try:
                # Usa subprocess.run para garantir que o terminal permaneça interativo
                subprocess.run(["aws", "configure", "sso"], check=True)
                
                # Verifica se agora existe uma configuração SSO válida
                if check_aws_sso_config():
                    console.print("\n✅ AWS SSO configurado com sucesso!", style="bold green")
                    
                    # Obtém a lista de profiles
                    profile_result = subprocess.run(
                        ["aws", "configure", "list-profiles"],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    profiles = profile_result.stdout.strip().split('\n')
                    
                    # Se só existe um profile, usa-o automaticamente
                    if len(profiles) == 1:
                        profile = profiles[0]
                        console.print(f"\n🔑 Utilizando o profile [bold green]{profile}[/] para login...", style="bold blue")
                    else:
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
                        else:
                            return
                
                    # Executa o login AWS SSO
                    console.print(f"\n🔑 Fazendo login com o profile [bold green]{profile}[/]...", style="bold blue")
                    
                    # Substituir capture_output por subprocess.run sem capturar a saída
                    subprocess.run(
                        ["aws", "sso", "login", "--profile", profile],
                        check=False  # Não lança exceção em caso de erro
                    )
                    
                    # Verifica se o login foi bem-sucedido
                    verify_result = subprocess.run(
                        ["aws", "sts", "get-caller-identity", "--profile", profile],
                        capture_output=True,
                        text=True,
                        check=False
                    )
                    
                    if verify_result.returncode != 0:
                        console.print(f"❌ Erro ao fazer login com o profile '{profile}'", style="bold red")
                        return
                else:
                    console.print("\n⚠️ Configuração AWS SSO não completada corretamente.", style="bold yellow")
                    return
            except subprocess.CalledProcessError:
                console.print(f"❌ Erro ao configurar o AWS SSO.", style="bold red")
                return
            
        else:
            # Lista os profiles disponíveis
            result = subprocess.run(
                ["aws", "configure", "list-profiles"],
                capture_output=True,
                text=True
            )
            profiles = result.stdout.strip().split('\n')
            
            # Adiciona a opção para criar um novo profile
            profiles.append("+ Adicionar novo profile")
            
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
                
                # Se a opção de adicionar novo profile foi selecionada
                if profile == "+ Adicionar novo profile":
                    console.print("\n📝 Iniciando configuração AWS SSO. Siga os passos abaixo:", style="bold blue")
                    console.print("   - SSO start URL: https://jera.awsapps.com/start", style="dim white")
                    console.print("   - SSO Region: us-east-1", style="dim white")
                    console.print("   - CLI default client Region: us-east-1", style="dim white")
                    console.print("   - CLI default output format: json", style="dim white")
                    console.print("   - CLI profile name: nome-do-seu-perfil", style="dim white")
                    
                    # Executa o comando tradicional para configurar o SSO
                    console.print("\n🔧 Executando configuração AWS SSO interativa...", style="bold blue")
                    try:
                        # Salva a lista atual de profiles antes da configuração
                        before_profiles = set(profiles) - set(["+ Adicionar novo profile"])
                        
                        # Usa subprocess.run para garantir que o terminal permaneça interativo
                        subprocess.run(["aws", "configure", "sso"], check=True)
                        
                        # Atualiza a lista de profiles
                        profile_result = subprocess.run(
                            ["aws", "configure", "list-profiles"],
                            capture_output=True,
                            text=True,
                            check=True
                        )
                        new_profiles = profile_result.stdout.strip().split('\n')
                        after_profiles = set(new_profiles)
                        
                        # Identifica os profiles adicionados
                        added_profiles = after_profiles - before_profiles
                        
                        # Mostra a lista atualizada para seleção
                        if added_profiles:
                            console.print(f"\n✅ Novo(s) profile(s) configurado(s) com sucesso: {', '.join(added_profiles)}", style="bold green")
                            questions = [
                                inquirer.List('profile',
                                            message="Selecione o profile para usar",
                                            choices=new_profiles,
                                            )
                            ]
                            answers = inquirer.prompt(questions)
                            
                            if answers:
                                profile = answers['profile']
                            else:
                                return
                        else:
                            # Mesmo que não tenha detectado novos profiles, permite selecionar um dos existentes
                            console.print("\n⚠️ Não foi possível detectar novos profiles, mas a configuração pode ter sido realizada.", style="bold yellow")
                            console.print("Por favor, selecione um profile existente para continuar:", style="bold blue")
                            
                            questions = [
                                inquirer.List('profile',
                                            message="Selecione o profile para usar",
                                            choices=new_profiles,
                                            )
                            ]
                            answers = inquirer.prompt(questions)
                            
                            if answers:
                                profile = answers['profile']
                            else:
                                return
                    except subprocess.CalledProcessError:
                        console.print(f"❌ Erro ao configurar o profile AWS SSO.", style="bold red")
                        return
                
                console.print(f"\n🔑 Fazendo login com o profile [bold green]{profile}[/]...", style="bold blue")
                
                # Substituir capture_output por subprocess.run sem capturar a saída
                subprocess.run(
                    ["aws", "sso", "login", "--profile", profile],
                    check=False  # Não lança exceção em caso de erro
                )
                
                # Verifica se o login foi bem-sucedido
                verify_result = subprocess.run(
                    ["aws", "sts", "get-caller-identity", "--profile", profile],
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                if verify_result.returncode != 0:
                    console.print(f"❌ Erro ao fazer login com o profile '{profile}'", style="bold red")
                    return
            
        console.print("\n✅ Login realizado com sucesso!", style="bold green")
        
    except Exception as e:
        console.print(f"\n❌ Erro ao fazer login: {str(e)}", style="bold red")
        if "The SSO session has expired" in str(e):
            console.print("A sessão SSO expirou. Tente novamente.", style="yellow") 

@click.command(name="clusters")
def clusters():
    """Lista todos os clusters Kubernetes configurados."""
    list_configured_clusters()

@click.command(name="login-azure")
def login_azure():
    """Faz login no Azure CLI de forma interativa."""
    try:
        # Verifica se o Azure CLI está instalado
        if not check_azure_cli_installed():
            console.print("\n❌ Azure CLI não está instalado!", style="bold red")
            console.print("\n📝 Para instalar o Azure CLI:", style="bold yellow")
            console.print("1. Linux/MacOS:", style="dim")
            console.print("   curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash", style="bold green")
            console.print("\n2. Windows:", style="dim")
            console.print("   https://docs.microsoft.com/pt-br/cli/azure/install-azure-cli-windows", style="bold green")
            console.print("\nInstale o Azure CLI e tente novamente.", style="bold yellow")
            return

        # Verifica se já existe uma sessão ativa
        if check_azure_session():
            current_subscription = get_azure_current_subscription()
            subscriptions = get_azure_subscriptions()
            
            console.print(f"\n✅ Você já está logado no Azure!", style="bold green")
            console.print(f"🔹 Assinatura atual: [bold blue]{current_subscription}[/]", style="dim")
            
            # Pergunta se quer mudar a assinatura
            choices = ["Continuar com a assinatura atual"] + subscriptions
            
            questions = [
                inquirer.List('subscription',
                             message="Deseja mudar a assinatura?",
                             choices=choices,
                             default="Continuar com a assinatura atual"
                             )
            ]
            answers = inquirer.prompt(questions)
            
            if answers and answers['subscription'] != "Continuar com a assinatura atual":
                subscription = answers['subscription']
                console.print(f"\n🔄 Mudando para a assinatura [bold blue]{subscription}[/]...", style="bold blue")
                
                if set_azure_subscription(subscription):
                    console.print(f"✅ Assinatura alterada com sucesso!", style="bold green")
                else:
                    console.print(f"❌ Erro ao alterar a assinatura.", style="bold red")
                    return
            
            return
        
        # Executa o login no Azure
        console.print("\n🔑 Iniciando login no Azure...", style="bold blue")
        console.print("Um navegador será aberto para você fazer login.", style="dim white")
        
        subprocess.run(
            ["az", "login"],
            check=False  # Não lança exceção em caso de erro
        )
        
        # Verifica se o login foi bem-sucedido
        if check_azure_session():
            console.print("\n✅ Login realizado com sucesso!", style="bold green")
            
            # Lista as assinaturas e permite selecionar
            subscriptions = get_azure_subscriptions()
            current = get_azure_current_subscription()
            
            if len(subscriptions) > 1:
                console.print(f"\nAssinatura atual: [bold blue]{current}[/]", style="dim")
                
                questions = [
                    inquirer.List('subscription',
                                 message="Selecione a assinatura que deseja usar",
                                 choices=subscriptions,
                                 default=current
                                 )
                ]
                answers = inquirer.prompt(questions)
                
                if answers and answers['subscription'] != current:
                    subscription = answers['subscription']
                    console.print(f"\n🔄 Mudando para a assinatura [bold blue]{subscription}[/]...", style="bold blue")
                    
                    if set_azure_subscription(subscription):
                        console.print(f"✅ Assinatura alterada com sucesso!", style="bold green")
                    else:
                        console.print(f"❌ Erro ao alterar a assinatura.", style="bold red")
                        return
            
            console.print("\n📋 Agora você pode usar os comandos 'init-azure' para configurar seu cluster AKS.", style="bold blue")
            
        else:
            console.print("\n❌ Falha ao fazer login no Azure.", style="bold red")
            return
        
    except Exception as e:
        console.print(f"\n❌ Erro ao fazer login: {str(e)}", style="bold red")

@click.command(name="init-azure")
@click.option('--cluster', '-c', help='Nome do cluster AKS para inicializar')
@click.option('--resource-group', '-g', help='Grupo de recursos do cluster AKS')
@click.option('--subscription', '-s', help='Assinatura Azure para usar')
def init_azure(cluster=None, resource_group=None, subscription=None):
    """Inicializa a configuração do kubectl para um cluster AKS."""
    try:
        # Verifica se o Azure CLI está instalado
        if not check_azure_cli_installed():
            console.print("\n❌ Azure CLI não está instalado!", style="bold red")
            console.print("\n📝 Para instalar o Azure CLI:", style="bold yellow")
            console.print("1. Linux/MacOS:", style="dim")
            console.print("   curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash", style="bold green")
            console.print("\n2. Windows:", style="dim")
            console.print("   https://docs.microsoft.com/pt-br/cli/azure/install-azure-cli-windows", style="bold green")
            console.print("\nInstale o Azure CLI e tente novamente.", style="bold yellow")
            return

        # Verifica se tem uma sessão Azure ativa
        if not check_azure_session():
            console.print("\n⚠️  Você não tem uma sessão Azure ativa!", style="bold yellow")
            console.print("\n📝 Use o comando 'jeracli login-azure' para fazer login primeiro.", style="bold blue")
            return

        # Verifica a assinatura atual
        current_subscription = get_azure_current_subscription()
        selected_subscription = subscription or current_subscription
        
        if subscription and subscription != current_subscription:
            console.print(f"\n🔄 Mudando para a assinatura [bold blue]{selected_subscription}[/]...", style="bold blue")
            
            if not set_azure_subscription(selected_subscription):
                console.print(f"❌ Erro ao alterar a assinatura.", style="bold red")
                return
        
        # Se não foi fornecido um cluster, lista os clusters disponíveis
        selected_cluster = cluster
        selected_resource_group = resource_group
        
        if not selected_cluster:
            console.print(f"\n🔍 Listando clusters AKS na assinatura [bold blue]{selected_subscription}[/]...", style="bold blue")
            
            try:
                # Obtém todos os clusters com seus respectivos grupos de recursos
                result = subprocess.run(
                    ["az", "aks", "list", "--query", "[].{name:name, resourceGroup:resourceGroup}", "-o", "json"],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    console.print(f"❌ Erro ao listar clusters AKS: {result.stderr}", style="bold red")
                    return
                
                clusters = json.loads(result.stdout)
                
                if not clusters:
                    console.print("❌ Não foram encontrados clusters AKS nesta assinatura.", style="bold red")
                    return
                
                # Obtém o cluster atual da configuração (se existir)
                current_cluster = None
                current_resource_group = None
                
                if 'azure_cluster' in config_data:
                    current_cluster = config_data['azure_cluster']
                    current_resource_group = config_data.get('azure_resource_group')
                
                # Monta opções para o usuário selecionar
                cluster_choices = []
                for c in clusters:
                    cluster_info = f"{c['name']} (Grupo: {c['resourceGroup']})"
                    # Marca o cluster atual
                    if c['name'] == current_cluster and c['resourceGroup'] == current_resource_group:
                        cluster_choices.append(f"{cluster_info} (atual)")
                    else:
                        cluster_choices.append(cluster_info)
                
                questions = [
                    inquirer.List('cluster',
                                message="Selecione o cluster AKS",
                                choices=cluster_choices,
                                )
                ]
                answers = inquirer.prompt(questions)
                
                if not answers:
                    return
                
                # Extrai o nome do cluster e o grupo de recursos da seleção
                selected_option = answers['cluster'].replace(" (atual)", "")
                
                # Tenta encontrar o cluster e grupo de recursos correspondentes
                found = False
                for c in clusters:
                    if selected_option == f"{c['name']} (Grupo: {c['resourceGroup']})":
                        selected_cluster = c['name']
                        selected_resource_group = c['resourceGroup']
                        found = True
                        break
                
                # Se não encontrou na forma exata, tenta extrair o nome e grupo diretamente
                if not found:
                    # Tenta extrair o nome e o grupo da string selecionada
                    # Formato esperado: "nome-do-cluster (Grupo: nome-do-grupo)"
                    import re
                    match = re.match(r"([^(]+)\s*\(Grupo:\s*([^)]+)\)", selected_option)
                    if match:
                        selected_cluster = match.group(1).strip()
                        selected_resource_group = match.group(2).strip()
                    else:
                        console.print("❌ Não foi possível extrair o nome do cluster e grupo de recursos da seleção.", style="bold red")
                        return
                
            except Exception as e:
                console.print(f"❌ Erro ao listar clusters Azure: {str(e)}", style="bold red")
                return
        
        # Verifica se temos o grupo de recursos quando o cluster está definido
        if selected_cluster and not selected_resource_group:
            console.print("❌ Grupo de recursos não informado para o cluster Azure.", style="bold red")
            console.print("📝 Você precisa fornecer o grupo de recursos para clusters AKS:", style="bold blue")
            console.print(f"  jeracli use-cluster {selected_cluster} -az -g NOME_DO_GRUPO", style="bold green")
            return
        
        # Configura kubectl para o cluster selecionado
        console.print(f"\n🔄 Configurando kubectl para o cluster [bold green]{selected_cluster}[/]...", style="bold blue")
        
        success, stdout, stderr = get_aks_credentials(
            selected_cluster, 
            resource_group=selected_resource_group, 
            subscription=selected_subscription
        )
        
        if success:
            # Atualiza a configuração
            config_data['azure_cluster'] = selected_cluster
            config_data['azure_resource_group'] = selected_resource_group
            config_data['azure_subscription'] = selected_subscription
            config_data['current_type'] = 'azure'
            
            # Salva a configuração
            os.makedirs(os.path.expanduser('~/.jera'), exist_ok=True)
            with open(config_path, 'w') as f:
                yaml.dump(config_data, f)
            
            console.print(f"✅ Cluster alterado para: [bold green]{selected_cluster}[/] (Azure AKS)", style="bold")
            console.print(f"📊 Detalhes:", style="bold blue")
            console.print(f"   Cluster: {selected_cluster}", style="dim")
            console.print(f"   Grupo de recursos: {selected_resource_group}", style="dim")
            console.print(f"   Assinatura: {selected_subscription}", style="dim")
            
            # Testa a conexão com o cluster
            test_cluster = subprocess.run(
                ["kubectl", "get", "nodes", "--request-timeout=5s"],
                capture_output=True,
                text=True,
                check=False
            )
            
            if test_cluster.returncode != 0:
                console.print("\n⚠️ A configuração foi atualizada, mas não foi possível conectar ao cluster.", style="bold yellow")
                console.print("📝 Isso pode ocorrer por:", style="bold blue")
                console.print("  • Problemas de conectividade de rede", style="dim white")
                console.print("  • Problemas de autenticação", style="dim white")
                console.print("  • Configurações adicionais podem ser necessárias", style="dim white")
                console.print("\nTente usar o seguinte comando para verificar a conexão:", style="bold blue")
                console.print("  kubectl get nodes", style="bold green")
            else:
                console.print("\n✅ Conexão com o cluster estabelecida com sucesso!", style="bold green")
            
            # Lista os clusters configurados após a alteração
            list_configured_clusters()
        else:
            console.print(f"❌ Erro ao configurar o cluster: {stderr}", style="bold red")
            return
        
    except Exception as e:
        console.print(f"\n❌ Erro ao inicializar o cluster: {str(e)}", style="bold red") 
#!/usr/bin/env python3

import click
import subprocess
import os
import yaml
from kubernetes import client, config
from rich.console import Console
from rich.table import Table
import inquirer
import json
import time

console = Console()

class KubeContext:
    def __init__(self):
        self.namespace = None

pass_context = click.make_pass_decorator(KubeContext, ensure=True)

@click.group()
@click.version_option(version='1.0.0', prog_name='Jera CLI')
@click.pass_context
def cli(ctx):
    """🚀 Jera CLI - Gerencie seus recursos na AWS e Kubernetes de maneira simples

    Uma CLI para facilitar operações comuns no cluster Kubernetes da Jera.
    
    Comandos Principais:
    
    ⚡ Configuração:
      init          Configura AWS SSO e kubectl para o cluster
      use          Define o namespace atual para operações
    
    📊 Visualização:
      pods         Lista todos os pods no namespace atual
      namespaces   Lista todos os namespaces disponíveis com status
      metrics      Mostra uso de CPU e memória dos pods
      url          Mostra informações dos Ingresses (hosts, endereços, portas)
    
    🔍 Operações em Pods:
      logs         Visualiza logs de um pod (com opção de follow)
      exec         Abre um shell interativo dentro do pod
      delete       Remove um pod do cluster (com confirmação)
    
    Fluxo básico de uso:
    
    1. Configure suas credenciais:
        $ jeracli init
    
    2. Selecione um namespace:
        $ jeracli use production
    
    3. Gerencie seus recursos:
        $ jeracli pods            # Lista pods
        $ jeracli logs           # Vê logs (interativo)
        $ jeracli metrics        # Monitora recursos
        $ jeracli exec meu-pod   # Acessa o pod
        $ jeracli url            # Ver URLs dos Ingresses
    
    Use --help em qualquer comando para mais informações:
        $ jeracli init --help
        $ jeracli logs --help
        etc.
    """
    ctx.obj = KubeContext()

def check_aws_sso_config():
    """Check if AWS SSO is configured properly"""
    try:
        # Verifica se existe o arquivo de configuração do SSO
        home = os.path.expanduser("~")
        config_file = os.path.join(home, ".aws", "config")
        
        if not os.path.exists(config_file):
            return False
            
        # Lê o arquivo de configuração
        with open(config_file, 'r') as f:
            config_content = f.read()
            
        # Verifica se as configurações necessárias estão presentes
        required_configs = [
            "sso_session",
            "sso_account_id",
            "sso_role_name",
            "region",
            "output"
        ]
        
        for config in required_configs:
            if config not in config_content:
                return False
                
        return True
    except Exception as e:
        console.print(f"Erro ao verificar configuração SSO: {str(e)}", style="bold red")
        return False

def configure_aws_sso():
    """Configure AWS SSO"""
    console.print("\n📝 Configurando AWS SSO...", style="bold blue")
    console.print("\nPor favor, tenha em mãos as seguintes informações:", style="bold yellow")
    console.print("1. SSO start URL (exemplo: https://jera.awsapps.com/start)")
    console.print("2. SSO Region (exemplo: us-east-1)")
    console.print("3. Nome do perfil que deseja criar (exemplo: jera-dev)")
    console.print("\nDicas de configuração:", style="bold green")
    console.print("- SSO start URL: Peça para alguém do time ou procure no 1Password")
    console.print("- SSO Region: us-east-1")
    console.print("- CLI default client Region: us-east-1")
    console.print("- CLI default output format: json")
    console.print("- CLI profile name: Use seu nome ou algo que identifique facilmente\n")
    
    input("Pressione Enter quando estiver pronto para continuar...")
    
    try:
        # Primeiro configuramos a sessão SSO
        console.print("\n1. Configurando sessão SSO...", style="bold blue")
        subprocess.run(["aws", "configure", "sso"], check=True)
        
        # Aguarda um momento para garantir que o arquivo foi escrito
        time.sleep(2)
        
        # Verifica se a configuração foi bem sucedida
        if check_aws_sso_config():
            console.print("✅ AWS SSO configurado com sucesso!", style="bold green")
            
            # Tenta fazer um teste simples para verificar se o perfil está funcionando
            try:
                subprocess.run(["aws", "sts", "get-caller-identity"], check=True, capture_output=True)
                console.print("✅ Perfil testado e funcionando!", style="bold green")
                return True
            except subprocess.CalledProcessError:
                console.print("⚠️ Perfil configurado, mas pode precisar fazer login.", style="bold yellow")
                return True
        else:
            console.print("❌ Configuração do AWS SSO incompleta ou incorreta.", style="bold red")
            console.print("\nDicas de resolução:", style="bold yellow")
            console.print("1. Verifique se você completou todos os passos da configuração")
            console.print("2. Certifique-se de que a URL do SSO está correta")
            console.print("3. Tente remover a configuração atual e começar novamente:")
            console.print("   rm -rf ~/.aws/config ~/.aws/credentials")
            return False
    except subprocess.CalledProcessError as e:
        console.print(f"❌ Erro ao configurar AWS SSO: {str(e)}", style="bold red")
        return False

def check_aws_sso_session():
    """Check if there's an active AWS SSO session"""
    try:
        # Primeiro tenta encontrar o profile configurado
        home = os.path.expanduser("~")
        config_file = os.path.join(home, ".aws", "config")
        
        if not os.path.exists(config_file):
            return False
            
        # Tenta com cada profile configurado
        result = subprocess.run(
            ["aws", "configure", "list-profiles"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            profiles = result.stdout.strip().split('\n')
            
            for profile in profiles:
                try:
                    result = subprocess.run(
                        ["aws", "sts", "get-caller-identity", "--profile", profile],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        return True
                except:
                    continue
                    
        return False
    except Exception as e:
        console.print(f"Erro ao verificar sessão SSO: {str(e)}", style="dim red")
        return False

@cli.command()
def init():
    """Inicializa a configuração do kubectl para o cluster da Jera.
    
    Verifica se você tem uma sessão AWS SSO ativa e configura o kubectl
    para acessar o cluster EKS da Jera.
    
    Requisitos:
    - AWS CLI instalado (aws --version)
    - Credenciais SSO configuradas (aws configure sso)
    - Acesso ao cluster EKS da Jera
    
    Se você não tiver o AWS CLI instalado, instale-o primeiro:
    - Linux/MacOS: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html
    - Windows: https://aws.amazon.com/cli/
    
    Exemplo:
        $ jeracli init
    """
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
        
        # Usa o primeiro profile que funcionar
        profile_used = None
        for profile in profiles:
            try:
                # Tenta usar o profile para atualizar o kubeconfig
                console.print(f"🔄 Tentando atualizar kubeconfig com profile {profile}...", style="bold blue")
                subprocess.run([
                    "aws", "eks", "update-kubeconfig",
                    "--name", "jera-cluster",
                    "--region", "us-east-1",
                    "--profile", profile
                ], check=True)
                profile_used = profile
                break
            except:
                continue
                
        if profile_used:
            console.print(f"✅ Configuração do kubectl atualizada com sucesso usando profile '{profile_used}'!", style="bold green")
        else:
            console.print("❌ Não foi possível encontrar um profile válido para acessar o cluster.", style="bold red")
            
    except subprocess.CalledProcessError as e:
        console.print(f"❌ Erro durante a inicialização: {str(e)}", style="bold red")

@cli.command()
@click.argument('namespace', required=False)
@pass_context
def use(ctx, namespace=None):
    """Seleciona o namespace atual para operações.
    
    Se o namespace não for fornecido, apresenta uma lista interativa
    de namespaces disponíveis. Caso contrário, seleciona o namespace
    especificado.
    
    Todos os comandos subsequentes (pods, logs, exec, delete) serão
    executados no namespace selecionado.
    
    Exemplos:
        $ jeracli use              # Seleciona namespace interativamente
        $ jeracli use production   # Seleciona namespace diretamente
    """
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
        ctx.namespace = selected_namespace
        os.makedirs(os.path.expanduser('~/.jera'), exist_ok=True)
        with open(os.path.expanduser('~/.jera/config'), 'w') as f:
            yaml.dump({'namespace': selected_namespace}, f)
            
        console.print(f"✅ Namespace alterado para: [bold green]{selected_namespace}[/]", style="bold")
    except Exception as e:
        console.print(f"❌ Erro ao alterar namespace: {str(e)}", style="bold red")

@cli.command()
def pods():
    """Lista todos os pods no namespace atual.
    
    Mostra uma tabela com informações sobre cada pod:
    - Nome do pod
    - Status atual
    - IP do pod
    - Idade do pod (tempo desde a criação)
    
    Requer que um namespace tenha sido selecionado usando 'jeracli use'.
    
    Exemplo:
        $ jeracli pods
    """
    try:
        # Load saved namespace
        namespace = None
        config_path = os.path.expanduser('~/.jera/config')
        if os.path.exists(config_path):
            with open(config_path) as f:
                config_data = yaml.safe_load(f)
                namespace = config_data.get('namespace')

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
            # Calcula a idade do pod
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
            
            table.add_row(
                pod.metadata.name,
                pod.status.phase,
                pod.status.pod_ip or "N/A",
                age_str
            )
        
        console.print(table)
    except Exception as e:
        console.print(f"❌ Erro ao listar pods: {str(e)}", style="bold red")

@cli.command()
@click.argument('pod_name', required=False)
@click.option('-f', '--follow', is_flag=True, help='Acompanha os logs em tempo real')
@click.option('-n', '--tail', type=int, default=None, help='Número de linhas para mostrar (do final)')
def logs(pod_name=None, follow=False, tail=None):
    """Visualiza logs de um pod no namespace atual.
    
    Se o nome do pod não for fornecido, apresenta uma lista interativa
    de pods disponíveis. Caso contrário, mostra os logs do pod especificado.
    
    Opções:
        -f, --follow    Acompanha os logs em tempo real
        -n, --tail N    Mostra as últimas N linhas do log
    
    Requer que um namespace tenha sido selecionado usando 'jeracli use'.
    
    Exemplos:
        $ jeracli logs                    # Seleciona pod interativamente
        $ jeracli logs meu-pod            # Mostra todos os logs do pod
        $ jeracli logs meu-pod -f         # Acompanha logs em tempo real
        $ jeracli logs meu-pod -n 100     # Mostra últimas 100 linhas
        $ jeracli logs meu-pod -f -n 100  # Acompanha últimas 100 linhas
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
                             message="Selecione um pod para ver os logs",
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
            
        # Monta o comando kubectl com as opções
        cmd = ["kubectl", "logs", "-n", namespace]
        
        if follow:
            cmd.append("-f")
            
        if tail is not None:
            cmd.extend(["--tail", str(tail)])
            
        cmd.append(selected_pod)
            
        # Use kubectl logs com as opções especificadas
        subprocess.run(cmd)
    except Exception as e:
        console.print(f"❌ Erro ao obter logs: {str(e)}", style="bold red")

@cli.command()
@click.argument('pod_name', required=False)
def exec(pod_name=None):
    """Executa um shell interativo dentro de um pod.
    
    Se o nome do pod não for fornecido, apresenta uma lista interativa
    de pods disponíveis. Caso contrário, abre um shell no pod especificado.
    
    Requer que um namespace tenha sido selecionado usando 'jeracli use'.
    
    Exemplos:
        $ jeracli exec              # Seleciona pod interativamente
        $ jeracli exec meu-pod      # Conecta diretamente ao pod especificado
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
                             message="Selecione um pod para conectar",
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
            
        # Mostra mensagem de conexão
        console.print(f"\n🔌 Conectando ao pod [bold cyan]{selected_pod}[/] no namespace [bold green]{namespace}[/]...", style="yellow")
        console.print("💡 Use [bold]exit[/] para sair do shell\n", style="dim")
            
        # Execute kubectl exec
        subprocess.run([
            "kubectl", "exec",
            "-it", selected_pod,
            "-n", namespace,
            "--", "/bin/sh"
        ])
    except Exception as e:
        console.print(f"❌ Erro ao executar shell no pod: {str(e)}", style="bold red")

@cli.command()
@click.argument('pod_name')
@click.option('--force', '-f', is_flag=True, help='Força a deleção do pod sem aguardar a finalização graciosa')
def delete(pod_name, force):
    """Deleta um pod específico do namespace atual.
    
    Solicita confirmação antes de deletar o pod para evitar
    exclusões acidentais.
    
    Opções:
        -f, --force    Força a deleção do pod sem aguardar a finalização graciosa
    
    Requer que um namespace tenha sido selecionado usando 'jeracli use'.
    
    Exemplos:
        $ jeracli delete meu-pod            # Deleção normal
        $ jeracli delete meu-pod --force    # Força a deleção
        $ jeracli delete meu-pod -f         # Força a deleção (forma curta)
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
        
        # Confirm deletion
        message = f"Tem certeza que deseja {'[bold red]FORÇAR[/] ' if force else ''}deletar o pod {pod_name}?"
        questions = [
            inquirer.Confirm('confirm',
                           message=message,
                           default=False)
        ]
        answers = inquirer.prompt(questions)
        
        if answers and answers['confirm']:
            cmd = ["kubectl", "delete", "pod", "-n", namespace]
            
            if force:
                cmd.extend(["--force", "--grace-period=0"])
                console.print(f"🚨 [bold red]Forçando[/] a deleção do pod {pod_name}...", style="yellow")
            else:
                console.print(f"🗑️ Deletando pod {pod_name}...", style="yellow")
            
            cmd.append(pod_name)
            subprocess.run(cmd, check=True)
            
            console.print(f"✅ Pod {pod_name} deletado com sucesso!", style="bold green")
    except Exception as e:
        console.print(f"❌ Erro ao deletar pod: {str(e)}", style="bold red")

@cli.command()
def namespaces():
    """📋 Lista todos os namespaces disponíveis no cluster"""
    try:
        # Carrega a configuração do kubernetes
        config.load_kube_config()
        v1 = client.CoreV1Api()
        
        # Cria uma tabela rica para exibir os namespaces
        table = Table(title="📋 Namespaces Disponíveis", show_header=True)
        table.add_column("Nome", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Idade", style="yellow")
        
        # Lista os namespaces
        namespaces = v1.list_namespace()
        
        for ns in namespaces.items:
            # Calcula a idade do namespace
            creation_time = ns.metadata.creation_timestamp
            age = time.time() - creation_time.timestamp()
            age_str = ""
            
            if age < 3600:  # menos de 1 hora
                age_str = f"{int(age/60)}m"
            elif age < 86400:  # menos de 1 dia
                age_str = f"{int(age/3600)}h"
            else:
                age_str = f"{int(age/86400)}d"
            
            table.add_row(
                ns.metadata.name,
                ns.status.phase,
                age_str
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"❌ Erro ao listar namespaces: {str(e)}", style="bold red")
        return

@cli.command()
@click.argument('namespace', required=False)
@click.argument('pod_name', required=False)
def metrics(namespace=None, pod_name=None):
    """Mostra o uso de recursos (CPU/Memória) dos pods.
    
    Se o namespace não for fornecido, apresenta uma lista interativa
    de namespaces disponíveis. Se o pod não for fornecido, mostra uma
    lista interativa de pods disponíveis.
    
    Opções disponíveis:
    - Ver recursos de todos os pods em um namespace
    - Ver recursos de um pod específico
    - Seleção interativa de namespace e pod
    - Total de recursos calculado ao ver múltiplos pods
    
    Requer que o Metrics Server esteja instalado no cluster.
    
    Exemplos:
        $ jeracli metrics                    # Seleciona namespace e pod interativamente
        $ jeracli metrics production         # Seleciona pod do namespace interativamente
        $ jeracli metrics production pod-123 # Mostra recursos do pod específico
    """
    try:
        config.load_kube_config()
        v1 = client.CoreV1Api()
        
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
                             message="Selecione o namespace para ver os recursos",
                             choices=available_namespaces,
                             )
            ]
            answers = inquirer.prompt(questions)
            
            if answers:
                namespace = answers['namespace']
            else:
                return

        # Se não foi fornecido um pod, mostra a lista interativa
        if not pod_name:
            # Get list of pods using kubectl
            result = subprocess.run(
                ["kubectl", "get", "pods", "-n", namespace, "-o", "name"],
                capture_output=True,
                text=True,
                check=True
            )
            
            pod_names = [pod.replace('pod/', '') for pod in result.stdout.strip().split('\n') if pod]
            
            if not pod_names:
                console.print(f"❌ Nenhum pod encontrado no namespace {namespace}.", style="bold red")
                return
            
            # Adiciona opção para ver todos os pods
            pod_names.insert(0, "📊 Todos os Pods")
            
            questions = [
                inquirer.List('pod',
                             message="Selecione um pod para ver os recursos",
                             choices=pod_names,
                             )
            ]
            answers = inquirer.prompt(questions)
            
            if answers:
                pod_name = answers['pod']
            else:
                return

        # Mostra mensagem de conexão
        if pod_name == "📊 Todos os Pods":
            console.print(f"\n🔄 Conectando ao namespace [bold green]{namespace}[/] e obtendo recursos de todos os pods...", style="yellow")
            pod_name = None
        else:
            console.print(f"\n🔄 Conectando ao namespace [bold green]{namespace}[/] e obtendo recursos do pod [bold cyan]{pod_name}[/]...", style="yellow")

        # Verifica se o Metrics Server está disponível
        try:
            if pod_name:
                result = subprocess.run(
                    ["kubectl", "top", "pod", pod_name, "-n", namespace],
                    capture_output=True,
                    text=True,
                    check=True
                )
            else:
                result = subprocess.run(
                    ["kubectl", "top", "pods", "-n", namespace],
                    capture_output=True,
                    text=True,
                    check=True
                )
        except subprocess.CalledProcessError as e:
            if "Metrics API not available" in e.stderr:
                console.print("\n❌ Metrics API não está disponível.", style="bold red")
                console.print("\nPara resolver:", style="bold yellow")
                console.print("1. Instale o Metrics Server:", style="dim")
                console.print("   kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml")
                console.print("\n2. Aguarde alguns minutos para inicialização", style="dim")
                console.print("3. Tente novamente\n", style="dim")
                return
            else:
                raise e
        
        # Cria uma tabela rica para exibir os recursos
        title = f"📊 Recursos dos Pods em [bold cyan]{namespace}[/]" if not pod_name else f"📊 Recursos do Pod [bold cyan]{pod_name}[/]"
        table = Table(title=title, show_header=True)
        table.add_column("Pod", style="cyan")
        table.add_column("CPU", style="green", justify="right")
        table.add_column("Memória", style="yellow", justify="right")
        
        # Processa a saída
        lines = result.stdout.strip().split('\n')[1:]  # Pula o cabeçalho
        for line in lines:
            parts = line.split()
            if len(parts) >= 3:
                pod_name = parts[0]
                cpu = parts[1]
                memory = parts[2]
                table.add_row(pod_name, cpu, memory)
        
        # Adiciona uma linha de total apenas se estiver mostrando múltiplos pods
        if len(lines) > 1:
            table.add_section()
            total_cpu = sum(float(line.split()[1].replace('m', '')) for line in lines)
            total_memory = sum(int(line.split()[2].replace('Mi', '')) for line in lines)
            table.add_row(
                "[bold]Total[/]",
                f"[bold]{total_cpu}m[/]",
                f"[bold]{total_memory}Mi[/]"
            )
        
        # Mostra a tabela
        console.print()
        console.print(table)
        console.print()
        
    except Exception as e:
        console.print(f"❌ Erro ao obter recursos: {str(e)}", style="bold red")

@cli.command()
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

@cli.command()
@click.argument('namespace', required=False)
def ingress(namespace=None):
    """Mostra as URLs dos Ingresses.
    
    Se o namespace não for fornecido, apresenta uma lista interativa
    de namespaces disponíveis. Mostra todas as regras de roteamento
    configuradas nos Ingresses do namespace.
    
    Exemplos:
        $ jeracli ingress              # Seleciona namespace interativamente
        $ jeracli ingress production   # Mostra Ingresses do namespace
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
                             message="Selecione o namespace para ver os Ingresses",
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

        # Para cada Ingress, cria uma tabela com suas regras
        for ing in ingresses.items:
            ingress_name = ing.metadata.name
            
            # Cria uma tabela rica para exibir as regras do Ingress
            table = Table(title=f"🌐 Regras do Ingress [bold cyan]{ingress_name}[/]", show_header=True)
            table.add_column("Host", style="cyan")
            table.add_column("Path", style="yellow")
            table.add_column("Serviço", style="green")
            table.add_column("Porta", style="blue", justify="right")
            
            # Processa as regras do Ingress
            for rule in ing.spec.rules:
                host = rule.host or "*"
                
                if rule.http and rule.http.paths:
                    for path in rule.http.paths:
                        service_name = path.backend.service.name
                        service_port = path.backend.service.port.number
                        path_pattern = path.path or "/"
                        
                        table.add_row(
                            host,
                            path_pattern,
                            service_name,
                            str(service_port)
                        )
            
            # Mostra a tabela
            console.print()
            console.print(table)
            
            # Se tiver TLS configurado, mostra os hosts seguros
            if ing.spec.tls:
                console.print("\n🔒 [bold yellow]Hosts HTTPS:[/]")
                for tls in ing.spec.tls:
                    for host in tls.hosts:
                        console.print(f"  https://{host}")
            
            console.print()
        
    except Exception as e:
        console.print(f"❌ Erro ao obter Ingresses: {str(e)}", style="bold red")

@cli.command(name="login-aws")
def login_aws():
    """Faz login no AWS SSO de forma interativa.
    
    Guia o usuário pelo processo de login no AWS SSO da Jera,
    verificando a configuração e abrindo o navegador para autenticação.
    
    Se for a primeira vez:
    1. Configura o AWS SSO com as informações da Jera
    2. Faz login no navegador
    
    Se já estiver configurado:
    1. Apenas renova o login
    
    Exemplo:
        $ jeracli login-aws
    """
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

@cli.command()
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

if __name__ == '__main__':
    cli() 
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
    
    Se você não tiver uma sessão ativa, o comando mostrará instruções
    sobre como configurar o AWS SSO e fazer login.
    
    Exemplo:
        $ jeracli init
    """
    try:
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
        
        for pod in pods.items:
            table.add_row(
                pod.metadata.name,
                pod.status.phase,
                pod.status.pod_ip or "N/A"
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
def delete(pod_name):
    """Deleta um pod específico do namespace atual.
    
    Solicita confirmação antes de deletar o pod para evitar
    exclusões acidentais.
    
    Requer que um namespace tenha sido selecionado usando 'jeracli use'.
    
    Exemplo:
        $ jeracli delete meu-pod-com-erro
        $ jeracli delete worker-pod-travado
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
        questions = [
            inquirer.Confirm('confirm',
                           message=f"Tem certeza que deseja deletar o pod {pod_name}?",
                           default=False)
        ]
        answers = inquirer.prompt(questions)
        
        if answers and answers['confirm']:
            subprocess.run(["kubectl", "delete", "pod", "-n", namespace, pod_name], check=True)
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

if __name__ == '__main__':
    cli() 
import click
from rich.console import Console
import inquirer
import yaml
import os
from kubernetes import client, config
import subprocess
from ..utils.kubernetes import check_aws_sso_config, check_aws_sso_session

console = Console()

@click.command()
def init():
    """Inicializa a configuração do kubectl para o cluster da Jera."""
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
        with open(os.path.expanduser('~/.jera/config'), 'w') as f:
            yaml.dump({'namespace': selected_namespace}, f)
            
        console.print(f"✅ Namespace alterado para: [bold green]{selected_namespace}[/]", style="bold")
    except Exception as e:
        console.print(f"❌ Erro ao alterar namespace: {str(e)}", style="bold red")

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
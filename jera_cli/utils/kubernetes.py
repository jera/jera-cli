from kubernetes import client, config
from rich.console import Console
import subprocess
import time
import os

console = Console()

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

def format_age(timestamp):
    """Formata a idade de um recurso baseado em seu timestamp"""
    age = time.time() - timestamp.timestamp()
    if age < 60:  # menos de 1 minuto
        return f"{int(age)}s"
    elif age < 3600:  # menos de 1 hora
        return f"{int(age/60)}m"
    elif age < 86400:  # menos de 1 dia
        return f"{int(age/3600)}h"
    else:
        return f"{int(age/86400)}d"

def get_pod_metrics(namespace):
    """Obtém métricas de uso dos pods em um namespace"""
    try:
        result = subprocess.run(
            ["kubectl", "top", "pods", "-n", namespace],
            capture_output=True,
            text=True,
            check=True
        )
        metrics_lines = result.stdout.strip().split('\n')[1:]  # Pula o cabeçalho
        metrics_dict = {}
        for line in metrics_lines:
            parts = line.split()
            if len(parts) >= 3:
                pod_name = parts[0]
                cpu = parts[1]
                memory = parts[2]
                metrics_dict[pod_name] = {
                    'cpu': cpu,
                    'memory': memory
                }
        return metrics_dict
    except subprocess.CalledProcessError:
        return {}

def parse_resource_value(value, resource_type='cpu'):
    """Converte valores de recursos (CPU/memória) para um formato padrão"""
    if not value:
        return 0
        
    if resource_type == 'cpu':
        if value.endswith('m'):
            return int(value[:-1])
        return int(float(value) * 1000)
    elif resource_type == 'memory':
        if value.endswith('Mi'):
            return int(value[:-2])
        elif value.endswith('Gi'):
            return int(float(value[:-2]) * 1024)
        elif value.endswith('Ki'):
            return int(value[:-2]) / 1024
    return 0 
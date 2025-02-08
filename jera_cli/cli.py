#!/usr/bin/env python3

import click
from rich.console import Console
from .commands.pods import pods, logs, exec
from .commands.metrics import pod_metrics, all_metrics
from .commands.config import init, use, login_aws

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
      login-aws    Faz login no AWS SSO de forma interativa
    
    📊 Visualização:
      pods         Lista todos os pods no namespace atual
      namespaces   Lista todos os namespaces disponíveis com status
      pod-metrics  Mostra análise detalhada de recursos dos pods
      all-metrics  Mostra análise detalhada de recursos de todos os pods
    
    🔍 Operações em Pods:
      logs         Visualiza logs de um pod (com opção de follow)
      exec         Abre um shell interativo dentro do pod
      delete       Remove um pod do cluster (com confirmação)
    
    Fluxo básico de uso:
    
    1. Configure suas credenciais:
        $ jeracli login-aws    # Faz login no SSO
        $ jeracli init         # Configura o kubectl
    
    2. Selecione um namespace:
        $ jeracli use production
    
    3. Gerencie seus recursos:
        $ jeracli pods            # Lista pods
        $ jeracli pod-metrics     # Vê métricas dos pods
        $ jeracli logs           # Vê logs (interativo)
        $ jeracli exec meu-pod   # Acessa o pod
    
    Use --help em qualquer comando para mais informações:
        $ jeracli init --help
        $ jeracli logs --help
        etc.
    """
    ctx.obj = KubeContext()

# Registra os comandos
cli.add_command(init)
cli.add_command(use)
cli.add_command(login_aws)
cli.add_command(pods)
cli.add_command(logs)
cli.add_command(exec)
cli.add_command(pod_metrics)
cli.add_command(all_metrics)

if __name__ == '__main__':
    cli() 
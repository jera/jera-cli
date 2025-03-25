#!/usr/bin/env python3

import click
from rich.console import Console
from .commands.commands import (
    pods, logs, exec, pods_by_node, describe, delete,
    pod_metrics, all_metrics,
    init, use, login_aws, use_cluster, clusters,
    nodes, namespaces, url
)

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
      use           Define o namespace atual para operações
      use-cluster   Alterna entre diferentes clusters Kubernetes
      clusters      Lista todos os clusters configurados
      login-aws     Faz login no AWS SSO de forma interativa
    
    📊 Visualização:
      pods         Lista todos os pods no namespace atual
      namespaces   Lista todos os namespaces disponíveis com status
      pod-metrics  Mostra análise detalhada de recursos dos pods
      all-metrics  Mostra análise detalhada de recursos de todos os pods
      url          Mostra as URLs dos Ingresses no namespace
    
    🔍 Operações em Pods:
      logs         Visualiza logs de um pod (com opção de follow)
      exec         Abre um shell interativo dentro do pod
    
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
        $ jeracli url            # Vê URLs dos Ingresses
    
    Use --help em qualquer comando para mais informações:
        $ jeracli init --help
        $ jeracli logs --help
        etc.
    """
    ctx.obj = KubeContext()

# Registra os comandos
cli.add_command(init)
cli.add_command(use)
cli.add_command(use_cluster)
cli.add_command(clusters)
cli.add_command(login_aws)
cli.add_command(pods)
cli.add_command(logs)
cli.add_command(exec)
cli.add_command(pod_metrics)
cli.add_command(all_metrics)
cli.add_command(nodes)
cli.add_command(pods_by_node)
cli.add_command(describe)
cli.add_command(namespaces)
cli.add_command(url)
cli.add_command(delete)

# Adiciona aliases
cli.add_command(login_aws, name='aws-login')

if __name__ == '__main__':
    cli() 
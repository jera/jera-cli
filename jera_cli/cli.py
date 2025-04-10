#!/usr/bin/env python3

import click
from rich.console import Console
from .commands.commands import (
    pods, logs, exec, pods_by_node, describe, delete,
    pod_metrics, all_metrics,
    init, use, login_aws, use_cluster, clusters,
    nodes, namespaces, urls, loadbalancer,
    pvs, pvcs, storage, node_metrics,
    login_azure, init_azure
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
    
    \b
    Comandos Principais:
    
    \b
    ⚡ Configuração:
      init          Configura AWS SSO e kubectl para o cluster
      init-azure    Configura Azure CLI e kubectl para o cluster AKS
      use           Define o namespace atual para operações
      use-cluster   Alterna entre diferentes clusters Kubernetes (AWS ou Azure)
      clusters      Lista todos os clusters configurados
      login-aws     Faz login no AWS SSO de forma interativa
      login-azure   Faz login no Azure de forma interativa
    
    \b
    📊 Visualização:
      pods         Lista todos os pods no namespace atual
      namespaces   Lista todos os namespaces disponíveis com status
      pod-metrics  Mostra análise detalhada de recursos dos pods
      all-metrics  Mostra análise detalhada de recursos de todos os pods
      urls         Mostra as URLs dos Ingresses (todos os namespaces)
      loadbalancer Mostra as URLs dos LoadBalancers (todos os namespaces)
      lb           Alias para loadbalancer
    
    \b
    💾 Armazenamento:
      pvs          Mostra os Persistent Volumes do cluster
      pvcs         Mostra os Persistent Volume Claims
      storage      Mostra uma visão consolidada de armazenamento
    
    \b
    🖥️ Nós:
      nodes        Lista todos os nós do cluster
      describe     Mostra informações detalhadas de um nó específico
      node-metrics Mostra métricas de utilização dos nós e top 5 pods
    
    \b
    🔍 Operações em Pods:
      logs         Visualiza logs de um pod (com opção de follow)
      exec         Abre um shell interativo dentro do pod
      delete       Deleta um ou mais pods no namespace atual
    
    \b
    Fluxo básico de uso:
    
    \b
    1. Configure suas credenciais:
       $ jeracli login-aws    # Faz login no SSO
       $ jeracli init         # Configura o kubectl
       
       # Ou para Azure:
       $ jeracli login-azure  # Faz login no Azure
       $ jeracli init-azure   # Configura o kubectl para AKS
    
    \b
    2. Selecione um namespace:
       $ jeracli use production
    
    \b
    3. Gerencie seus recursos:
       $ jeracli pods            # Lista pods
       $ jeracli pod-metrics     # Vê métricas dos pods
       $ jeracli logs            # Vê logs (interativo)
       $ jeracli logs -a         # Vê logs de todos os pods
       $ jeracli exec meu-pod    # Acessa o pod
       $ jeracli urls            # Vê URLs dos Ingresses em todos os namespaces
       $ jeracli urls -n prod    # Filtra por namespace específico
       $ jeracli lb              # Vê URLs dos LoadBalancers
       $ jeracli pvcs            # Vê Persistent Volume Claims
       $ jeracli node-metrics    # Vê utilização de recursos nos nós
       
       # Alternar clusters:
       $ jeracli use-cluster              # Usa o tipo atual (AWS ou Azure)
       $ jeracli use-cluster -s           # Alterna entre AWS e Azure
       $ jeracli use-cluster --aws        # Força o uso de clusters AWS
       $ jeracli use-cluster -az          # Força o uso de clusters Azure
       $ jeracli use-cluster my-cluster   # Usa cluster AWS específico
       $ jeracli use-cluster my-aks -az -g my-group  # Usa cluster Azure específico
    
    \b
    Use --help em qualquer comando para mais informações:
       $ jeracli init --help
       $ jeracli use-cluster --help
       etc.
    """
    ctx.obj = KubeContext()

# Registra os comandos
cli.add_command(init)
cli.add_command(use)
cli.add_command(use_cluster)
cli.add_command(clusters)
cli.add_command(login_aws)
cli.add_command(login_azure)
cli.add_command(init_azure)
cli.add_command(pods)
cli.add_command(logs)
cli.add_command(exec)
cli.add_command(pod_metrics)
cli.add_command(all_metrics)
cli.add_command(nodes)
cli.add_command(pods_by_node)
cli.add_command(describe)
cli.add_command(namespaces)
cli.add_command(urls)
cli.add_command(delete)
cli.add_command(loadbalancer)
cli.add_command(pvs)
cli.add_command(pvcs)
cli.add_command(storage)
cli.add_command(node_metrics)

# Adiciona aliases
cli.add_command(login_aws, name='aws-login')
cli.add_command(login_azure, name='azure-login')
cli.add_command(loadbalancer, name='lb')

if __name__ == '__main__':
    cli() 
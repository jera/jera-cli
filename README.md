![Jera Logo](https://jera.com.br/images/logo-jera-light.svg)

# Jera CLI 🚀

Uma CLI simplificada para gerenciar recursos de Kubernetes na AWS e Azure.

## Instalação Rápida

### Pré-requisitos
- Python 3.8+
- Sistema operacional: Linux (Ubuntu) ou macOS

```bash
# Clone o repositório
git clone https://github.com/jera/jera-cli.git
cd jera-cli

# Instale a CLI
./install.sh
```

## Uso Básico

### Opção 1: AWS
```bash
# Faça login no AWS SSO
jeracli login-aws

# Configure o acesso ao cluster EKS
jeracli init
```

### Opção 2: Azure
```bash
# Faça login no Azure
jeracli login-azure

# Configure o acesso ao cluster AKS
jeracli init-azure
```

### 3. Selecionar Namespace
```bash
# Escolha um namespace para trabalhar
jeracli use production
```

### Alternando entre Clusters
```bash
# Liste todos os clusters configurados
jeracli clusters

# Alterne para outro cluster (AWS ou Azure)
jeracli use-cluster

# Alterne explicitamente entre AWS e Azure
jeracli use-cluster -s

# Escolha um cluster AWS específico
jeracli use-cluster meu-cluster-aws

# Escolha um cluster Azure específico
jeracli use-cluster meu-cluster-aks -az -g meu-grupo-recursos
```

## Comparação com kubectl

A Jera CLi nasceu muito por que toda vez que precisavamos fazer algo entre namespaces tinhamos que toda hora escrever kubectl, o que para mim estava sendo horrivel ja que é um comando "muito" grande, além de ter que escrever '-n meu-namespace' quase toda hora....
Dai a Jera CLI simplifica as operações diárias no Kubernetes, abstraindo a complexidade dos comandos do kubectl. Veja abaixo uma comparação dos comandos mais frequentes:

| Funcionalidade               | Jera CLI                        | kubectl                                                    |
|------------------------------|--------------------------------|-----------------------------------------------------------|
| **Seleção de contexto**      | `jeracli use-cluster`          | `kubectl config use-context <context>`                    |
| **Configuração de cluster AWS** | `jeracli init`              | `aws eks update-kubeconfig --name <cluster>`              |
| **Configuração de cluster Azure** | `jeracli init-azure`      | `az aks get-credentials --resource-group <rg> --name <cluster>` |
| **Seleção de namespace**     | `jeracli use <namespace>`      | `kubectl config set-context --current --namespace=<namespace>` |
| **Listar pods**              | `jeracli pods`                 | `kubectl get pods`                                         |
| **Ver logs de um pod**       | `jeracli logs <pod>`           | `kubectl logs <pod>`                                       |
| **Executar shell em um pod** | `jeracli exec <pod>`           | `kubectl exec -it <pod> -- /bin/sh`                       |
| **Ver detalhes de um pod**   | `jeracli describe <pod>`       | `kubectl describe pod <pod>`                              |
| **Listar serviços**          | `jeracli loadbalancer` ou `lb` | `kubectl get svc`                                         |
| **Listar ingresses**         | `jeracli urls`                 | `kubectl get ingress --all-namespaces`                    |
| **Listar nós**               | `jeracli nodes`                | `kubectl get nodes`                                       |
| **Ver métricas de nós**      | `jeracli node-metrics`         | `kubectl top nodes`                                       |
| **Ver volumes persistentes** | `jeracli pvs`                  | `kubectl get pv`                                          |
| **Ver claims de volumes**    | `jeracli pvcs`                 | `kubectl get pvc --all-namespaces`                        |

### Principais vantagens da Jera CLI:

- **Simplicidade**: Comandos mais curtos e intuitivos
- **Interatividade**: Muitos comandos oferecem seleção interativa quando não especificados todos os parâmetros
- **Integração com cloud**: Gerencia automaticamente a autenticação com AWS e Azure
- **Comandos consolidados**: Agrega múltiplas operações kubectl em um único comando
- **Visualização otimizada**: Saída formatada e focada nas informações mais relevantes

### Comandos Principais

#### Listar Pods
```bash
# Lista pods no namespace atual
jeracli pods
```

#### Ver Logs
```bash
# Ver logs de um pod (interativo)
jeracli logs
```

#### Executar Shell em um Pod
```bash
# Abrir shell em um pod
jeracli exec
```

## Comandos Disponíveis

- `login-aws`: Faz login no AWS SSO interativamente
- `login-azure`: Faz login no Azure interativamente
- `init`: Configura AWS SSO e kubectl para cluster EKS
- `init-azure`: Configura kubectl para cluster AKS
- `use-cluster`: Alterna entre clusters (AWS EKS ou Azure AKS)
- `use`: Define namespace atual
- `pods`: Lista pods
- `logs`: Visualiza logs de pods
- `exec`: Abre shell em pods
- `describe`: Mostra detalhes de pods
- `urls`: Lista URLs de Ingresses
- `loadbalancer`: Lista URLs dos LoadBalancers
- `lb`: Alias para loadbalancer
- `pvs`: Mostra Persistent Volumes
- `pvcs`: Mostra Persistent Volume Claims
- `storage`: Visão consolidada de armazenamento
- `nodes`: Lista nós do cluster
- `node-metrics`: Mostra métricas de utilização dos nós

## Desenvolvimento

### Configuração do Ambiente

1. Clone o repositório
```bash
git clone https://github.com/jera/jera-cli.git
cd jera-cli
```

2. Crie um ambiente virtual
```bash
python -m venv .venv
source .venv/bin/activate
```

3. Instale as dependências
```bash
pip install -e .
```

### Padrões de Desenvolvimento

#### Branches
- `feature/`: Para novas funcionalidades
- `fix/`: Para correções de bugs
- `improvement/`: Para melhorias em funcionalidades existentes

#### Commits
Use o padrão de commits semânticos:
- `feat:` Nova funcionalidade
- `fix:` Correção de bug
- `docs:` Alterações na documentação
- `style:` Formatação de código
- `refactor:` Refatoração
- `test:` Adição/modificação de testes
- `chore:` Tarefas de manutenção

### Exemplo de Commit
```bash
git commit -m "feat: adiciona opção de filtro por status nos pods"
```

### Pull Request
1. Crie uma branch para sua alteração
2. Faça suas modificações
3. Teste localmente
4. Crie um Pull Request com descrição clara

## Suporte

Em caso de dúvidas, entre em contato com a equipe de desenvolvimento.

## Licença

[Informações sobre a licença]

## Exemplos de Uso

### Cenário 1: Investigando um Pod com Problema
```bash
# Liste todos os pods
jeracli pods

# Veja os logs de um pod específico
jeracli logs meu-pod-nome

# Obtenha detalhes completos do pod
jeracli describe meu-pod-nome
```

### Cenário 2: Acessando um Container
```bash
# Abra um shell interativo em um pod
jeracli exec meu-pod-nome

# Execute um comando específico em um pod
jeracli exec meu-pod-nome -- ls /app
```

### Cenário 3: Gerenciando Namespaces
```bash
# Liste todos os namespaces disponíveis
jeracli namespaces

# Mude para um namespace específico
jeracli use production

# Veja os pods no namespace atual
jeracli pods
```

### Cenário 4: Verificando URLs de Ingress
```bash
# Liste URLs de Ingress em todos os namespaces
jeracli urls

# Liste URLs de Ingress em um namespace específico
jeracli urls -n staging

# Liste URLs dos LoadBalancers
jeracli lb
```

### Cenário 5: Análise de Recursos
```bash
# Veja métricas de todos os pods
jeracli pod-metrics

# Veja métricas de pods em um namespace específico
jeracli pod-metrics production

# Veja métricas dos nós do cluster
jeracli node-metrics

# Veja métricas de um nó específico
jeracli node-metrics nome-do-no
```

### Cenário 6: Visualizando Nós do Cluster
```bash
# Liste todos os nós do cluster
jeracli nodes

# Veja detalhes de um nó específico
jeracli describe node meu-node-nome
```

### Cenário 7: Gerenciando Armazenamento
```bash
# Listar todos os Persistent Volumes do cluster
jeracli pvs

# Ver informações detalhadas dos PVs
jeracli pvs -d

# Listar Persistent Volume Claims em todos os namespaces
jeracli pvcs

# Listar PVCs em um namespace específico
jeracli pvcs -n production

# Selecionar um namespace interativamente
jeracli pvcs -s

# Ver visão consolidada de armazenamento
jeracli storage

# Ver visão detalhada com filtro por namespace
jeracli storage -n production -d
```

### Cenário 8: Deletando Pods
```bash
# Deleta um pod específico
jeracli delete meu-pod

# Deleta múltiplos pods
jeracli delete pod1 pod2

# Força a deleção de um pod
jeracli delete meu-pod --force

# Deleta todos os pods do namespace atual
jeracli delete --all

# Força a deleção de todos os pods
jeracli delete --all --force
```

### Cenário 9: Trabalhando com Múltiplos Clusters
```bash
# AWS EKS
jeracli login-aws
jeracli init

# Azure AKS
jeracli login-azure
jeracli init-azure

# Alternar entre os clusters configurados
jeracli use-cluster

# Alternar explicitamente entre AWS e Azure
jeracli use-cluster -s

# Forçar o uso de Azure
jeracli use-cluster -az

# Forçar o uso de AWS
jeracli use-cluster --aws

# Especificar um cluster Azure com seu grupo de recursos
jeracli use-cluster meu-cluster-aks -az -g meu-grupo-recursos
```

### Dicas Adicionais
- Use `jeracli --help` para ver todos os comandos disponíveis
- Adicione `-h` ou `--help` após qualquer comando para ver opções específicas
  ```bash
  jeracli pods --help
  jeracli logs --help
  jeracli use-cluster --help
  ```
# Jera CLI 🚀

Uma CLI simplificada para gerenciar recursos da Jera na AWS.

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

### 1. Login na AWS
```bash
# Faça login no AWS SSO
jeracli login-aws
```

### 2. Inicialização do Kubectl
```bash
# Configure o acesso ao cluster
jeracli init
```

### 3. Selecionar Namespace
```bash
# Escolha um namespace para trabalhar
jeracli use production
```

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

- `init`: Configura AWS SSO e kubectl
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

### Dicas Adicionais
- Use `jeracli --help` para ver todos os comandos disponíveis
- Adicione `-h` ou `--help` após qualquer comando para ver opções específicas
  ```bash
  jeracli pods --help
  jeracli logs --help
  ```
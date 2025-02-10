# Jera CLI

Uma CLI simplificada para gerenciar recursos da Jera na AWS.

> 💡 **Dica**: Além do comando `jeracli`, você também pode usar o comando mais curto `jcli`. Os dois comandos são idênticos e podem ser usados de forma intercambiável.

## Pré-requisitos

Antes de instalar a CLI, certifique-se de ter:

1. **Python 3.8+**
   ```bash
   python --version
   ```

2. **AWS CLI**
   - É necessário ter o AWS CLI instalado e configurado
   - Será instalado automaticamente pelo script de instalação se não estiver presente
   - Instalação:
     - Linux/MacOS: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html
     - Windows: https://aws.amazon.com/cli/
   - Verifique a instalação:
     ```bash
     aws --version
     ```

3. **kubectl**
   - Necessário para interagir com o cluster
   - Será instalado automaticamente pelo script de instalação se não estiver presente
   - Se preferir instalar manualmente:
     - Linux: 
       ```bash
       curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
       sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
       ```
     - MacOS:
       ```bash
       brew install kubectl
       ```
     - Windows:
       ```bash
       choco install kubernetes-cli
       ```
   - Verifique a instalação:
     ```bash
     kubectl version --client
     ```
   - A configuração do kubectl será feita automaticamente pelo comando `init`

4. **Acesso ao cluster EKS da Jera**
   - Você precisa ter acesso ao AWS SSO da Jera
   - As credenciais serão configuradas durante o `init`

## Instalação

```bash
git clone https://github.com/jera/jera-cli.git && cd jera-cli && ./install.sh
```

O script de instalação irá:
1. Instalar a CLI globalmente em `/opt/jera-cli`
2. Criar um comando global `jeracli` disponível em qualquer diretório
3. Configurar um ambiente virtual isolado para as dependências

Nota: O script solicitará sua senha sudo para criar o comando global.

## Configuração Inicial

Após a instalação, você precisa configurar o acesso:

1. **Verifique o AWS CLI**:
   ```bash
   aws --version
   ```
   Se não estiver instalado, instale seguindo os links acima.

2. **Configure o AWS SSO**:
   ```bash
   aws configure sso
   ```
   - SSO start URL: https://jera.awsapps.com/start
   - SSO Region: us-east-1
   - CLI default client Region: us-east-1
   - CLI default output format: json
   - CLI profile name: seu-nome

3. **Inicialize a CLI**:
   ```bash
   jeracli init
   ```
   Este comando irá:
   - Verificar a instalação do AWS CLI
   - Configurar o acesso ao AWS SSO
   - Configurar o kubectl para o cluster

## Desenvolvimento

Se você deseja contribuir ou fazer melhorias na CLI, siga estes passos para configurar o ambiente de desenvolvimento:

### 1. Clone o repositório
```bash
git clone https://github.com/jera/jera-cli.git
cd jera-cli
```

### 2. Crie uma branch para suas alterações
```bash
git checkout -b feature/nome-da-sua-feature
# ou
git checkout -b fix/nome-do-seu-fix
```

Convenções de nomes para branches:
- `feature/`: Para novas funcionalidades
- `fix/`: Para correções de bugs
- `improvement/`: Para melhorias em funcionalidades existentes
- Use nomes descritivos e em inglês
- Use hífens para separar palavras

### 3. Crie e ative um ambiente virtual
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/MacOS
# ou
.venv\Scripts\activate  # Windows
```

### 4. Instale as dependências em modo de desenvolvimento
```bash
pip install -e .
```

### 5. Estrutura do Projeto
```
jera_cli/
├── __init__.py           # Exporta a CLI e define a versão
├── __main__.py          # Ponto de entrada para execução direta do módulo
├── cli.py               # Definição principal da CLI
├── commands/            # Módulo com os comandos
│   ├── __init__.py
│   ├── config.py       # Comandos de configuração (init, use, login-aws)
│   ├── metrics.py      # Comandos de métricas (pod-metrics, all-metrics)
│   └── pods.py         # Comandos de pods (pods, logs, exec)
└── utils/              # Módulo com funções utilitárias
    ├── __init__.py
    └── kubernetes.py   # Funções auxiliares para Kubernetes
```

### 6. Fazendo alterações

1. Faça suas alterações nos arquivos apropriados dentro do pacote `jera_cli/`
2. Teste localmente usando `python -m jera_cli [comando]`
3. Para testar a instalação global, execute `./install.sh`

### 7. Processo de Contribuição

1. **Desenvolvimento**:
   - Nunca faça commits diretamente na branch `main`
   - Sempre crie uma nova branch para suas alterações
   - Faça commits pequenos e descritivos
   - Teste suas alterações localmente

2. **Enviando alterações**:
   ```bash
   # Adicione suas alterações
   git add .
   
   # Faça o commit (use mensagens descritivas)
   git commit -m "feat: adiciona opção de filtro por status nos pods"
   
   # Envie para o repositório remoto
   git push origin feature/nome-da-sua-feature
   ```

3. **Criando Merge Request**:
   - Acesse o repositório no GitLab
   - Crie um novo Merge Request (MR)
   - Use um título claro e descritivo
   - Descreva suas alterações detalhadamente
   - Adicione labels apropriadas
   - Solicite revisão de outro desenvolvedor

4. **Convenções de Commits**:
   - `feat:` Nova funcionalidade
   - `fix:` Correção de bug
   - `docs:` Alterações na documentação
   - `style:` Formatação, ponto e vírgula, etc
   - `refactor:` Refatoração de código
   - `test:` Adição/modificação de testes
   - `chore:` Alterações em arquivos de build, etc

5. **Checklist antes do MR**:
   - [ ] Código testado localmente
   - [ ] Documentação atualizada
   - [ ] Testes adicionados/atualizados
   - [ ] Branch atualizada com a main
   - [ ] Convenções de código seguidas
   - [ ] Mensagens de commit adequadas

### 8. Dicas de Desenvolvimento

- Use `python -m jera_cli --help` para ver todos os comandos disponíveis
- Cada comando tem sua própria função decorada com `@cli.command()`
- A CLI usa as seguintes bibliotecas principais:
  - `click`: Para criar a interface de linha de comando
  - `rich`: Para formatação e cores no terminal
  - `inquirer`: Para interfaces interativas
  - `kubernetes`: Para interagir com o cluster
  - `PyYAML`: Para manipulação de arquivos YAML

- Mantenha a consistência com o estilo de código existente
- Adicione mensagens informativas e coloridas usando o `rich`
- Faça validações adequadas antes de executar operações
- Mantenha a documentação atualizada
- Teste todas as alterações antes de submeter

### 7. Organização dos Comandos

Os comandos da CLI estão organizados em módulos por categoria:

1. **Comandos de Configuração** (`commands/config.py`):
   - `init`: Configuração inicial do kubectl e AWS SSO
   - `use`: Seleção de namespace
   - `login-aws`: Login no AWS SSO

2. **Comandos de Pods** (`commands/pods.py`):
   - `pods`: Listagem de pods
   - `logs`: Visualização de logs
   - `exec`: Shell interativo em pods
   - `delete`: Remoção de pods

3. **Comandos de Métricas** (`commands/metrics.py`):
   - `pod-metrics`: Análise de recursos por namespace
   - `all-metrics`: Análise de recursos de todo o cluster

4. **Comandos de Ingress** (`commands/ingress.py`):
   - `url`: Visualização de URLs e detalhes dos Ingresses

5. **Utilitários** (`utils/kubernetes.py`):
   - Funções auxiliares para Kubernetes
   - Formatação de métricas e idade
   - Verificação de configuração AWS

Para adicionar um novo comando:
1. Identifique o módulo apropriado em `commands/`
2. Adicione sua função com o decorador `@click.command()`
3. Registre o comando em `cli.py`
4. Atualize a documentação se necessário

## Verificando a Instalação

Após a instalação, você pode verificar se está tudo funcionando corretamente:

```bash
jeracli --version
```

## Comandos Disponíveis

### Inicialização

```bash
jeracli init
```
Este comando irá:
- Fazer login na AWS usando SSO
- Configurar o kubectl para o cluster da Jera

### Selecionar Namespace

```bash
jeracli use <namespace>
```
Define o namespace atual para operações subsequentes.
- Se o namespace não for fornecido, apresenta uma lista interativa
- Salva o namespace selecionado para uso em outros comandos

### Listar Pods

```bash
jeracli pods
```
Lista todos os pods no namespace atual.
- Mostra nome, status e IP de cada pod
- Requer que um namespace tenha sido selecionado

### Listar Namespaces

```bash
jeracli namespaces
```
Lista todos os namespaces disponíveis no cluster.
- Mostra nome, status e idade de cada namespace
- Formatação colorida para melhor visualização

### Ver Logs

```bash
jeracli logs [pod] [-f] [-n N]
```
Permite visualizar logs de um pod.
- Se o pod não for fornecido, apresenta uma lista interativa
- Opções:
  - `-f, --follow`: Acompanha logs em tempo real
  - `-n, --tail N`: Mostra as últimas N linhas
- Requer que um namespace tenha sido selecionado

### Executar Shell em um Pod

```bash
jeracli exec <pod>
```
Abre um shell interativo dentro do pod.
- Se o pod não for fornecido, apresenta uma lista interativa
- Permite executar comandos dentro do container
- Requer que um namespace tenha sido selecionado

### Deletar Pod

```bash
jeracli delete <pod> [--force]
jeracli delete --all [--force]
```
Remove um pod específico ou todos os pods do cluster.
- Solicita confirmação antes de deletar
- Opções:
  - `--force, -f`: Força a deleção do pod sem aguardar a finalização graciosa
  - `--all, -a`: Deleta todos os pods do namespace atual
- Requer que um namespace tenha sido selecionado

### Análise de Recursos

```bash
jeracli resources [namespace]
```
Mostra uma análise detalhada dos recursos dos pods em um namespace.
- Se o namespace não for fornecido, apresenta uma lista interativa
- Exibe uma tabela com:
  - Recursos alocados (requests/limits) para cada pod
  - Recursos em uso atual
  - Porcentagem de utilização (uso/alocado)
  - Total de recursos do namespace
- Requer o Metrics Server instalado no cluster
- Mostra um resumo final com totais de CPU e memória

Exemplos:
```bash
jeracli resources              # Seleciona namespace interativamente
jeracli resources production   # Mostra recursos do namespace
```

### Ver Detalhes do Pod

```bash
jeracli describe [pod]
```
Mostra informações detalhadas de um pod.
- Se o pod não for fornecido, apresenta uma lista interativa
- Mostra informações como:
  - Status detalhado e condições
  - Labels e anotações
  - Informações dos containers
  - Volumes montados
  - Secrets utilizadas (volumes, env vars, envFrom)
  - Eventos recentes
- Requer que um namespace tenha sido selecionado

Exemplos:
```bash
jeracli describe              # Seleciona pod interativamente
jeracli describe meu-pod      # Mostra detalhes do pod especificado
```

### Login no AWS SSO

```bash
jeracli login-aws
```
Faz login no AWS SSO de forma interativa.

Se for a primeira vez:
1. Configura o AWS SSO com as informações da Jera
2. Solicita um nome para o profile
3. Abre o navegador para autenticação

Se já estiver configurado:
1. Lista os profiles disponíveis
2. Permite selecionar qual usar
3. Renova o login no navegador

Dicas:
- Use este comando quando sua sessão expirar
- Mais simples que o `aws sso login`
- Configuração automática na primeira vez
- Seleção interativa de profiles

### Ver URLs dos Ingresses

```bash
jeracli url [namespace] [ingress]
```
Mostra informações dos Ingresses em um formato similar ao `kubectl get ingress`.
- Se o namespace não for fornecido, apresenta uma lista interativa
- Mostra:
  - Nome do Ingress
  - Hosts configurados
  - Endereço do LoadBalancer
  - Portas disponíveis (80/443)
  - Idade do Ingress

Exemplos:
```bash
jeracli url                      # Seleciona namespace interativamente
jeracli url production           # Mostra todos os Ingresses do namespace
jeracli url production meu-app   # Mostra Ingress específico
```

### Ver Nós do Cluster

```bash
jeracli nodes
```
Lista todos os nós do cluster com informações detalhadas:
- Nome e status do nó (Ready/NotReady)
- Roles (control-plane, worker)
- Versão do Kubernetes
- Recursos disponíveis (CPU/Memória)
- Uso atual de recursos (requer metrics-server)
- Idade do nó

### Análise Geral de Recursos

```bash
jeracli general-metrics
```
Mostra uma análise detalhada dos recursos de todos os pods em todos os namespaces.
- Exibe uma tabela com:
  - Recursos alocados (requests/limits) para cada pod
  - Recursos em uso atual
  - Porcentagem de utilização
  - Total de recursos por namespace
  - Total geral de todos os namespaces
- Requer o Metrics Server instalado no cluster
- Mostra um resumo final com totais de CPU e memória de todo o cluster

### Listar Pods por Nó

```bash
jeracli pods-by-node [namespace]
```
Mostra todos os pods agrupados por nó.
- Se nenhum namespace for especificado, lista pods de todos os namespaces
- Se um namespace for fornecido, lista pods apenas desse namespace
- Exibe pods de cada nó em uma tabela separada
- Mostra namespace, nome, status, estado de ready e tempo de vida dos pods
- Inclui um resumo com total de nós e pods

Exemplos:
```bash
jeracli pods-by-node                # Lista pods de todos os namespaces
jeracli pods-by-node production     # Lista pods do namespace production
```
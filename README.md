# Jera CLI

Uma CLI simplificada para gerenciar recursos da Jera na AWS.

## Instalação

```bash
git clone https://github.com/jera/jera-cli.git && cd jera-cli && ./install.sh
```

O script de instalação irá:
1. Instalar a CLI globalmente em `/opt/jera-cli`
2. Criar um comando global `jeracli` disponível em qualquer diretório
3. Configurar um ambiente virtual isolado para as dependências

Nota: O script solicitará sua senha sudo para criar o comando global.

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
jera-cli/
├── jera_cli.py      # Arquivo principal com a implementação da CLI
├── setup.py         # Configuração do pacote e dependências
├── install.sh       # Script de instalação global
└── README.md        # Documentação
```

### 6. Fazendo alterações

1. Faça suas alterações no arquivo `jera_cli.py`
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

## Verificando a Instalação

Após a instalação, você pode verificar se está tudo funcionando corretamente:

```bash
jeracli --version
```

## Pré-requisitos

- Python 3.8+
- AWS CLI configurado
- kubectl instalado
- Acesso ao cluster EKS da Jera

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

### Listar Pods

```bash
jeracli pods
```
Lista todos os pods no namespace atual.

### Listar Namespaces

```bash
jeracli namespaces
```
Lista todos os namespaces disponíveis no cluster, mostrando o nome, status e idade de cada um.

### Ver Logs

```bash
jeracli logs
```
Permite selecionar um pod e ver seus logs.

### Executar Shell em um Pod

```bash
jeracli exec <nome-do-pod>
```
Abre um shell interativo dentro do pod especificado.

### Deletar Pod

```bash
jeracli delete <nome-do-pod>
```
Deleta o pod especificado (com confirmação).

### Ver Métricas dos Pods

```bash
jeracli metrics [namespace] [pod]
```
Mostra o uso de CPU e memória dos pods em um namespace.
- Se o namespace não for fornecido, apresenta uma lista interativa
- Se o pod não for fornecido, apresenta uma lista interativa dos pods do namespace
- Opção de ver recursos de todos os pods ou de um pod específico
- Requer o Metrics Server instalado no cluster
- Mostra uma tabela com uso de CPU e memória
- Calcula o total de recursos utilizados (quando vendo múltiplos pods)

Exemplos:
```bash
jeracli metrics                    # Seleciona namespace e pod interativamente
jeracli metrics production         # Seleciona pod do namespace interativamente
jeracli metrics production pod-123 # Mostra recursos do pod específico
```

### Ver URLs dos Ingresses

```bash
jeracli url [namespace] [ingress]
```
Mostra informações dos Ingresses em um formato similar ao `kubectl get ingress`.
- Se o namespace não for fornecido, apresenta uma lista interativa
- Mostra nome, hosts, endereço e portas de cada Ingress
- Indica a idade de cada Ingress
- Similar ao comando `kubectl get ingress` mas com formatação melhorada

Exemplos:
```bash
jeracli url                      # Seleciona namespace interativamente
jeracli url production           # Mostra todos os Ingresses do namespace
jeracli url production meu-app   # Mostra Ingress específico
```

### Ver Ingresses

```
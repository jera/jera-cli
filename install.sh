#!/bin/bash

# Cores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}🚀 Instalando Jera CLI...${NC}\n"

# Verifica se está rodando como sudo
if [ "$EUID" -ne 0 ]; then 
    echo -e "${YELLOW}⚠️  Executando com sudo para instalação global...${NC}"
    sudo "$0" "$@"
    exit $?
fi

# Função para instalar Python e pip no Ubuntu
install_python_ubuntu() {
    echo -e "${YELLOW}📦 Instalando Python 3.10+ no Ubuntu...${NC}"
    
    # Adiciona repositório para versões mais recentes do Python
    apt-get update
    apt-get install -y software-properties-common
    add-apt-repository -y ppa:deadsnakes/ppa
    apt-get update
    
    # Instala Python 3.10 e pip apenas se não estiverem instalados
    if ! dpkg -s python3.10 &> /dev/null; then
        apt-get install -y python3.10 python3.10-venv python3.10-dev
        
        # Define Python 3.10 como padrão
        update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1
        update-alternatives --set python3 /usr/bin/python3.10
    else
        echo -e "${GREEN}✅ Python 3.10 já está instalado.${NC}"
    fi
    
    # Instala pacotes de desenvolvimento e pip
    apt-get install -y python3-pip python3-dev python3-setuptools python3-wheel
    
    echo -e "${GREEN}✅ Pacotes de desenvolvimento Python instalados.${NC}"
}

# Função para instalar Python e pip no macOS
install_python_macos() {
    echo -e "${YELLOW}📦 Instalando Python 3.10+ no macOS via Homebrew...${NC}"
    
    # Verifica se o Homebrew está instalado
    if ! command -v brew &> /dev/null; then
        echo -e "${YELLOW}🍺 Instalando Homebrew...${NC}"
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi
    
    # Instala Python 3.10 apenas se não estiver instalado
    if ! brew list python@3.10 &> /dev/null; then
        brew install python@3.10
        
        # Adiciona ao PATH
        echo 'export PATH="/usr/local/opt/python@3.10/bin:$PATH"' >> ~/.zshrc
        echo 'export PATH="/usr/local/opt/python@3.10/bin:$PATH"' >> ~/.bash_profile
        
        # Recarrega o shell
        source ~/.zshrc
        source ~/.bash_profile
    else
        echo -e "${GREEN}✅ Python 3.10 já está instalado via Homebrew.${NC}"
    fi
    
    # Instala pacotes de desenvolvimento
    brew install python-setuptools python-wheel
    
    echo -e "${GREEN}✅ Pacotes de desenvolvimento Python instalados.${NC}"
}

# Função para verificar e instalar Python
check_python() {
    # Verifica se Python 3.8+ está instalado
    if ! command -v python3 &> /dev/null; then
        echo -e "${YELLOW}⚠️  Python 3 não encontrado. Instalando...${NC}"
        
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            # Linux (Ubuntu)
            install_python_ubuntu
            
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            install_python_macos
            
        else
            echo -e "${RED}❌ Sistema operacional não suportado para instalação automática do Python.${NC}"
            echo -e "${YELLOW}Por favor, instale manualmente o Python 3.8+.${NC}"
            exit 1
        fi
    fi
    
    # Verifica a versão do Python de forma mais robusta
    PYTHON_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
    PYTHON_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')
    
    # Verifica se a versão é maior ou igual a 3.8
    if [[ $PYTHON_MAJOR -lt 3 ]] || [[ $PYTHON_MAJOR -eq 3 && $PYTHON_MINOR -lt 8 ]]; then
        echo -e "${RED}❌ Python ${PYTHON_MAJOR}.${PYTHON_MINOR} não é suportado. Instale Python 3.8+.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Python ${PYTHON_MAJOR}.${PYTHON_MINOR} verificado com sucesso!${NC}"
}

# Função para verificar e instalar pip
check_pip() {
    if ! command -v pip3 &> /dev/null; then
        echo -e "${YELLOW}⚠️  pip não encontrado. Instalando...${NC}"
        
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            # Linux (Ubuntu)
            apt-get install -y python3-pip python3-setuptools
            
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            brew install python-pip
            
        else
            echo -e "${RED}❌ Sistema operacional não suportado para instalação automática do pip.${NC}"
            echo -e "${YELLOW}Por favor, instale manualmente o pip.${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}✅ pip já está instalado.${NC}"
    fi
    
    # Usa pip do sistema para atualizar
    python3 -m pip install --upgrade pip setuptools wheel
    
    echo -e "${GREEN}✅ pip e pacotes básicos atualizados com sucesso!${NC}"
}

# Chama as funções de verificação e instalação
check_python
check_pip

# Verifica se o AWS CLI está instalado
check_aws_cli() {
    if ! command -v aws &> /dev/null; then
        echo -e "${YELLOW}⚠️  AWS CLI não encontrado. Instalando...${NC}"
        
        # Detecta o sistema operacional
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            # Linux
            echo -e "${YELLOW}📦 Baixando AWS CLI para Linux...${NC}"
            curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
            apt-get update && apt-get install -y unzip
            unzip awscliv2.zip
            ./aws/install
            rm -rf aws awscliv2.zip
            
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            echo -e "${YELLOW}📦 Instalando AWS CLI via Homebrew...${NC}"
            brew install awscli
            
        else
            echo -e "${RED}❌ Sistema operacional não suportado para instalação automática do AWS CLI.${NC}"
            echo -e "${YELLOW}Por favor, instale manualmente:${NC}"
            echo -e "Windows: https://aws.amazon.com/cli/"
            echo -e "Linux/MacOS: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
            exit 1
        fi
        
        # Verifica se a instalação foi bem sucedida
        if command -v aws &> /dev/null; then
            echo -e "${GREEN}✅ AWS CLI instalado com sucesso!${NC}"
        else
            echo -e "${RED}❌ Falha ao instalar AWS CLI.${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}✅ AWS CLI já está instalado.${NC}"
    fi
}

# Verifica se o kubectl está instalado
check_kubectl() {
    if ! command -v kubectl &> /dev/null; then
        echo -e "${YELLOW}⚠️  kubectl não encontrado. Instalando...${NC}"
        
        # Detecta o sistema operacional
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            # Linux
            echo -e "${YELLOW}📦 Baixando kubectl para Linux...${NC}"
            curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
            install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
            rm -f kubectl
            
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            echo -e "${YELLOW}📦 Instalando kubectl via Homebrew...${NC}"
            brew install kubectl
            
        else
            echo -e "${RED}❌ Sistema operacional não suportado para instalação automática do kubectl.${NC}"
            echo -e "${YELLOW}Por favor, instale manualmente seguindo:${NC}"
            echo -e "https://kubernetes.io/docs/tasks/tools/install-kubectl/"
            exit 1
        fi
        
        # Verifica se a instalação foi bem sucedida
        if command -v kubectl &> /dev/null; then
            echo -e "${GREEN}✅ kubectl instalado com sucesso!${NC}"
        else
            echo -e "${RED}❌ Falha ao instalar kubectl.${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}✅ kubectl já está instalado.${NC}"
    fi
}

# Define os diretórios
INSTALL_DIR="/opt/jera-cli"
WRAPPER_SCRIPT="/usr/local/bin/jeracli"
ALIAS_SCRIPT="/usr/local/bin/jcli"

# Verifica e instala o AWS CLI se necessário
check_aws_cli

# Verifica e instala o kubectl se necessário
check_kubectl

# Remove o comando global
if [ -f "$WRAPPER_SCRIPT" ]; then
    echo -e "${YELLOW}🔄 Removendo instalação anterior...${NC}"
    rm -f "$WRAPPER_SCRIPT"
    rm -f "$ALIAS_SCRIPT"
fi

# Remove o diretório de instalação
if [ -d "$INSTALL_DIR" ]; then
    rm -rf "$INSTALL_DIR"
fi

# Cria diretório de instalação
echo -e "${YELLOW}📁 Criando diretório de instalação...${NC}"
mkdir -p "$INSTALL_DIR"
cp -r . "$INSTALL_DIR"

# Cria ambiente virtual no diretório de instalação
echo -e "${YELLOW}🔧 Criando ambiente virtual...${NC}"
cd "$INSTALL_DIR"
python3 -m venv .venv

# Ativa o ambiente virtual e instala dependências
source .venv/bin/activate

# Atualiza pip e setuptools
echo -e "${YELLOW}📦 Atualizando ferramentas de instalação...${NC}"
pip install --upgrade pip setuptools wheel

echo -e "${YELLOW}📦 Instalando dependências...${NC}"
pip install --use-pep517 -e .

# Cria o wrapper script
cat > "$WRAPPER_SCRIPT" << 'EOF'
#!/bin/bash
INSTALL_DIR="/opt/jera-cli"
VENV="$INSTALL_DIR/.venv"

# Ativa o ambiente virtual e executa o comando
source "$VENV/bin/activate"
python3 -m jera_cli "$@"
EOF

# Cria o link simbólico para o comando alternativo
ln -s "$WRAPPER_SCRIPT" "$ALIAS_SCRIPT"

# Torna o wrapper executável
chmod +x "$WRAPPER_SCRIPT"

# Ajusta as permissões
chown -R $(logname):$(logname) "$INSTALL_DIR"
chown $(logname):$(logname) "$WRAPPER_SCRIPT"
chown -h $(logname):$(logname) "$ALIAS_SCRIPT"

echo -e "\n${GREEN}✅ Jera CLI instalada com sucesso!${NC}"
echo -e "${YELLOW}Os comandos ${GREEN}jeracli${YELLOW} e ${GREEN}jcli${YELLOW} agora estão disponíveis globalmente.${NC}"
echo -e "\n${YELLOW}Para verificar a instalação:${NC}"
echo -e "${GREEN}jeracli --version${NC}"
echo -e "${GREEN}jcli --version${NC}"

# Verifica se o AWS CLI precisa ser configurado
if ! aws configure list &> /dev/null; then
    echo -e "\n${YELLOW}⚠️  AWS CLI ainda não está configurado.${NC}"
    echo -e "${YELLOW}Execute o comando abaixo para configurar:${NC}"
    echo -e "${GREEN}aws configure sso${NC}"
    echo -e "\nDicas de configuração:"
    echo -e "- SSO start URL: https://jera.awsapps.com/start"
    echo -e "- SSO Region: us-east-1"
    echo -e "- CLI default client Region: us-east-1"
    echo -e "- CLI default output format: json"
fi 
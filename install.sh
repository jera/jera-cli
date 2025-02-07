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

# Define o diretório de instalação
INSTALL_DIR="/opt/jera-cli"
WRAPPER_SCRIPT="/usr/local/bin/jeracli"

# Verifica se python3 está instalado
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 não encontrado. Por favor, instale o Python 3.8 ou superior.${NC}"
    exit 1
fi

# Verifica a versão do Python
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
if (( $(echo "$PYTHON_VERSION >= 3.12" | bc -l) )); then
    echo -e "${YELLOW}⚠️  Python 3.12 detectado. Garantindo compatibilidade...${NC}"
fi

# Verifica se pip está instalado
if ! command -v pip &> /dev/null; then
    echo -e "${RED}❌ pip não encontrado. Por favor, instale o pip.${NC}"
    exit 1
fi

# Verifica e instala o AWS CLI se necessário
check_aws_cli

# Verifica e instala o kubectl se necessário
check_kubectl

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
pip install -e .

# Cria o script wrapper
echo -e "${YELLOW}📝 Criando comando global...${NC}"
cat > "$WRAPPER_SCRIPT" << EOL
#!/bin/bash
source $INSTALL_DIR/.venv/bin/activate
$INSTALL_DIR/.venv/bin/jeracli "\$@"
EOL

# Torna o wrapper executável
chmod +x "$WRAPPER_SCRIPT"

# Ajusta as permissões
chown -R $(logname):$(logname) "$INSTALL_DIR"
chown $(logname):$(logname) "$WRAPPER_SCRIPT"

echo -e "\n${GREEN}✅ Jera CLI instalada com sucesso!${NC}"
echo -e "${YELLOW}O comando ${GREEN}jeracli${YELLOW} agora está disponível globalmente.${NC}"
echo -e "\n${YELLOW}Para verificar a instalação:${NC}"
echo -e "${GREEN}jeracli --version${NC}"

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
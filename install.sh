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
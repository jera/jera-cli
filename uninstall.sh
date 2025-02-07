#!/bin/bash

# Cores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}🗑️  Desinstalando Jera CLI...${NC}\n"

# Verifica se está rodando como sudo
if [ "$EUID" -ne 0 ]; then 
    echo -e "${YELLOW}⚠️  Executando com sudo para desinstalação...${NC}"
    sudo "$0" "$@"
    exit $?
fi

# Define os diretórios
INSTALL_DIR="/opt/jera-cli"
WRAPPER_SCRIPT="/usr/local/bin/jeracli"

# Remove o comando global
if [ -f "$WRAPPER_SCRIPT" ]; then
    echo -e "${YELLOW}🗑️  Removendo comando global...${NC}"
    rm -f "$WRAPPER_SCRIPT"
fi

# Remove o diretório de instalação
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}🗑️  Removendo diretório de instalação...${NC}"
    rm -rf "$INSTALL_DIR"
fi

# Remove configurações locais
echo -e "${YELLOW}🗑️  Removendo configurações locais...${NC}"
rm -rf ~/.jera

echo -e "\n${GREEN}✅ Jera CLI desinstalado com sucesso!${NC}" 
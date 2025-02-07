#!/bin/bash

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Função de log
log() {
    echo -e "${GREEN}[LOG]${NC} $1"
}

# Função de erro
error() {
    echo -e "${RED}[ERRO]${NC} $1"
}

# Diagnóstico de Volume no Namespace Específico
diagnose_namespace_volumes() {
    local NAMESPACE="jera-signoz"
    
    echo -e "${YELLOW}🔍 Diagnóstico de Volumes no Namespace $NAMESPACE:${NC}"
    
    # PVCs no namespace
    echo -e "${GREEN}PVCs:${NC}"
    kubectl get pvc -n "$NAMESPACE"
    
    # Detalhes dos volumes
    echo -e "\n${GREEN}Detalhes dos Volumes:${NC}"
    kubectl get pv | grep "$NAMESPACE"
    
    # Pods usando volumes
    echo -e "\n${GREEN}Pods com Volumes:${NC}"
    kubectl get pods -n "$NAMESPACE" -o wide | grep -E "VOLUME|pvc"
}

# Listar volumes detalhados
list_detailed_volumes() {
    local NAMESPACE="jera-signoz"
    
    echo -e "${YELLOW}🔍 Volumes Detalhados no Namespace $NAMESPACE:${NC}"
    
    kubectl get pvc -n "$NAMESPACE" -o custom-columns="\
NAMESPACE:.metadata.namespace,\
NAME:.metadata.name,\
STATUS:.status.phase,\
VOLUME:.spec.volumeName,\
STORAGE:.spec.resources.requests.storage,\
STORAGECLASS:.spec.storageClassName"
}

# Verificar status de anexo dos volumes
check_volume_attachment() {
    local NAMESPACE="jera-signoz"
    
    echo -e "${YELLOW}🔒 Status de Anexo dos Volumes:${NC}"
    
    kubectl get pv | while read -r line; do
        pv_name=$(echo "$line" | awk '{print $1}')
        status=$(echo "$line" | awk '{print $5}')
        
        # Verificar detalhes do PV
        kubectl describe pv "$pv_name" | grep -E "Claim:|Node Affinity:|Status:"
        echo "---"
    done
}

# Menu principal
main_menu() {
    while true; do
        echo -e "${GREEN}===== DIAGNÓSTICO DE VOLUMES =====${NC}"
        echo "1. Diagnóstico Completo de Volumes"
        echo "2. Listar Volumes Detalhados"
        echo "3. Verificar Status de Anexo"
        echo "4. Sair"

        read -p "Escolha uma opção: " choice

        case $choice in
            1) diagnose_namespace_volumes ;;
            2) list_detailed_volumes ;;
            3) check_volume_attachment ;;
            4) exit 0 ;;
            *) error "Opção inválida" ;;
        esac

        read -p "Pressione Enter para continuar..."
    done
}

# Executar
main_menu 
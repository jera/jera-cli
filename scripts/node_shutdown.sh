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

# Listar status do nó
check_node_status() {
    local NODE_NAME=$1
    
    echo -e "${YELLOW}🔍 Status do Nó: $NODE_NAME${NC}"
    
    # Status do nó
    kubectl describe node "$NODE_NAME"
    
    # Pods no nó
    echo -e "\n${GREEN}Pods no Nó:${NC}"
    kubectl get pods -o wide --field-selector spec.nodeName="$NODE_NAME"
}

# Forçar remoção de pods
force_pods_removal() {
    local NODE_NAME=$1
    
    log "🧹 Removendo pods do nó $NODE_NAME"
    
    # Listar e remover pods
    kubectl get pods -o wide --field-selector spec.nodeName="$NODE_NAME" | \
    while read -r line; do
        POD=$(echo "$line" | awk '{print $1}')
        NAMESPACE=$(echo "$line" | awk '{print $2}')
        
        log "Removendo pod $POD no namespace $NAMESPACE"
        
        # Forçar remoção
        kubectl delete pod "$POD" -n "$NAMESPACE" --grace-period=0 --force
    done
}

# Desligar nó
shutdown_node() {
    local NODE_NAME=$1
    
    # Cordon (impedir novos pods)
    log "🚫 Cordoning node $NODE_NAME"
    kubectl cordon "$NODE_NAME"
    
    # Drenar pods
    log "🚧 Draining node $NODE_NAME"
    kubectl drain "$NODE_NAME" --ignore-daemonsets --force
    
    # Forçar remoção de pods restantes
    force_pods_removal "$NODE_NAME"
    
    # Verificar status final
    check_node_status "$NODE_NAME"
}

# Menu principal
main_menu() {
    echo -e "${GREEN}===== DESLIGAMENTO DE NÓ =====${NC}"
    
    # Listar nós
    kubectl get nodes
    
    read -p "Digite o nome do nó para desligar: " NODE_NAME
    
    read -p "Confirma desligamento do nó $NODE_NAME? (s/n): " confirm
    
    if [[ $confirm == [sS] ]]; then
        shutdown_node "$NODE_NAME"
    else
        echo "❌ Operação cancelada"
    fi
}

# Executar
main_menu 
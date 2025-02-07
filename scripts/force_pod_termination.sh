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

# Métodos de Força de Terminação
force_pod_termination() {
    local POD_NAME=$1
    local NAMESPACE=$2

    # Método 1: Graceful Delete com timeout
    log "🔹 Método 1: Delete Gracioso com Timeout"
    kubectl delete pod "$POD_NAME" -n "$NAMESPACE" --grace-period=10 --force

    # Método 2: Patch para remover finalizers
    log "🔹 Método 2: Remover Finalizers"
    kubectl patch pod "$POD_NAME" -n "$NAMESPACE" -p '{"metadata":{"finalizers":null}}' --type=merge

    # Método 3: Deletar com opção force
    log "🔹 Método 3: Delete Forçado"
    kubectl delete pod "$POD_NAME" -n "$NAMESPACE" --grace-period=0 --force

    # Método 4: Patch de status
    log "🔹 Método 4: Patch de Status"
    kubectl patch pod "$POD_NAME" -n "$NAMESPACE" -p '{"status":{"phase":"Failed"}}' --type=merge
}

# Listar pods travados
list_stuck_pods() {
    local NAMESPACE=${1:-default}

    echo -e "${YELLOW}🔍 Pods Travados no Namespace $NAMESPACE:${NC}"
    
    kubectl get pods -n "$NAMESPACE" | grep -E "Terminating|Error|CrashLoopBackOff"
}

# Menu de seleção
select_pod_to_terminate() {
    echo "🔍 Namespaces disponíveis:"
    kubectl get namespaces

    read -p "Digite o namespace: " NAMESPACE
    
    echo -e "\n🔍 Pods no namespace $NAMESPACE:"
    kubectl get pods -n "$NAMESPACE"

    read -p "Digite o nome do pod para forçar terminação: " POD_NAME

    # Confirmar terminação
    read -p "Confirma terminação forçada de $POD_NAME? (s/n): " confirm

    if [[ $confirm == [sS] ]]; then
        force_pod_termination "$POD_NAME" "$NAMESPACE"
    else
        echo "❌ Operação cancelada"
    fi
}

# Menu principal
main_menu() {
    while true; do
        echo -e "${GREEN}===== FORÇA DE TERMINAÇÃO DE POD =====${NC}"
        echo "1. Forçar Terminação de Pod"
        echo "2. Listar Pods Travados"
        echo "3. Sair"

        read -p "Escolha uma opção: " choice

        case $choice in
            1) select_pod_to_terminate ;;
            2) 
                read -p "Digite o namespace (deixe em branco para default): " ns
                list_stuck_pods "${ns:-default}"
                ;;
            3) exit 0 ;;
            *) error "Opção inválida" ;;
        esac

        read -p "Pressione Enter para continuar..."
    done
}

# Executar
main_menu 
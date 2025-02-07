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

# Função para verificar e ignorar PDB
bypass_pdb_eviction() {
    local POD=$1
    local NAMESPACE=$2

    # Verificar se existe PDB para o pod
    PDB=$(kubectl get poddisruptionbudget -n "$NAMESPACE" -o jsonpath="{.items[?(@.spec.selector.matchLabels.app=='${POD}')].metadata.name}")

    if [ -n "$PDB" ]; then
        error "Pod $POD tem PDB: $PDB. Forçando bypass..."

        # Remover o PDB temporariamente
        kubectl delete poddisruptionbudget "$PDB" -n "$NAMESPACE"

        # Aguardar um momento para garantir remoção
        sleep 5

        # Drenar node com força total
        kubectl drain "$NODE" \
            --ignore-daemonsets \
            --delete-emptydir-data \
            --force \
            --grace-period=0 \
            --timeout=120s \
            --pod-selector="app!=${POD}"

        # Recriar o PDB (opcional, dependendo do comportamento desejado)
        # kubectl create -f <(kubectl get poddisruptionbudget "$PDB" -n "$NAMESPACE" -o yaml | sed "s/name: $PDB/name: $PDB-restored/")
    else
        # Drenagem padrão
        kubectl drain "$NODE" \
            --ignore-daemonsets \
            --delete-emptydir-data \
            --force \
            --grace-period=0
    fi
}

# Função de drenagem segura
drain_node_safely() {
    local NODE=$1

    log "🚧 Iniciando drenagem do nó: $NODE"

    # Listar pods críticos
    CRITICAL_PODS=$(kubectl get pods --all-namespaces -o wide | grep "$NODE" | grep -E "ebs-csi|kube-proxy|calico")

    # Cordon node
    kubectl cordon "$NODE"

    # Tentar drenar pods
    for pod_info in $CRITICAL_PODS; do
        POD=$(echo "$pod_info" | awk '{print $2}')
        NAMESPACE=$(echo "$pod_info" | awk '{print $1}')
        
        bypass_pdb_eviction "$POD" "$NAMESPACE"
    done

    # Drenar node completamente
    kubectl drain "$NODE" \
        --ignore-daemonsets \
        --delete-emptydir-data \
        --force
}

# Menu de seleção
select_nodes() {
    echo "🔍 Nós disponíveis:"
    kubectl get nodes

    read -p "Digite o nome do nó de origem para drenar: " SOURCE_NODE
    read -p "Digite o nome do nó de destino: " TARGET_NODE

    # Confirmar drenagem
    read -p "Confirma drenagem de $SOURCE_NODE para $TARGET_NODE? (s/n): " confirm

    if [[ $confirm == [sS] ]]; then
        drain_node_safely "$SOURCE_NODE"
    else
        echo "❌ Operação cancelada"
    fi
}

# Executar
select_nodes
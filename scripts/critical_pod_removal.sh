#!/bin/bash

# Função para remover pods críticos de sistema
remove_system_pods() {
    local NODE_NAME=$1
    local SYSTEM_PODS=(
        "aws-node"
        "coredns"
        "ebs-csi-controller"
        "ebs-csi-node"
        "kube-proxy"
    )

    echo "🚨 Removendo pods críticos do nó $NODE_NAME"

    for pod_prefix in "${SYSTEM_PODS[@]}"; do
        # Encontrar pods no nó específico
        kubectl get pods -A | grep "$pod_prefix" | grep "$NODE_NAME" | while read -r line; do
            POD=$(echo "$line" | awk '{print $2}')
            NAMESPACE=$(echo "$line" | awk '{print $1}')

            echo "🔹 Removendo pod: $POD no namespace $NAMESPACE"

            # Estratégias de remoção
            kubectl delete pod "$POD" -n "$NAMESPACE" --grace-period=0 --force
            
            # Tentar patch de finalizers
            kubectl patch pod "$POD" -n "$NAMESPACE" -p '{"metadata":{"finalizers":null}}' --type=merge
        done
    done
}

# Função para lidar com DaemonSets
handle_daemonsets() {
    local NODE_NAME=$1
    
    echo "🔄 Gerenciando DaemonSets no nó $NODE_NAME"
    
    # Listar DaemonSets
    kubectl get ds -A | tail -n +2 | while read -r line; do
        NAMESPACE=$(echo "$line" | awk '{print $1}')
        DAEMONSET=$(echo "$line" | awk '{print $2}')
        
        # Patch para ignorar nó específico
        kubectl patch ds "$DAEMONSET" -n "$NAMESPACE" \
            --type json \
            -p='[{"op": "add", "path": "/spec/template/spec/affinity", "value": {"nodeAffinity": {"requiredDuringSchedulingIgnoredDuringExecution": {"nodeSelectorTerms": [{"matchExpressions": [{"key": "kubernetes.io/hostname", "operator": "NotIn", "values": ["'$NODE_NAME'"]}]}]}}}}]'
    done
}

# Função principal de remoção
force_node_removal() {
    local NODE_NAME=$1

    # Cordon node
    kubectl cordon "$NODE_NAME"

    # Remover pods críticos
    remove_system_pods "$NODE_NAME"

    # Gerenciar DaemonSets
    handle_daemonsets "$NODE_NAME"

    # Drenar node
    kubectl drain "$NODE_NAME" \
        --ignore-daemonsets \
        --delete-emptydir-data \
        --force

    # Verificar status final
    kubectl get nodes
}

# Menu de seleção
select_node() {
    echo "🔍 Nós disponíveis:"
    kubectl get nodes

    read -p "Digite o nome do nó para remoção forçada: " NODE_NAME
    read -p "Confirma remoção de $NODE_NAME? (s/n): " confirm

    if [[ $confirm == [sS] ]]; then
        force_node_removal "$NODE_NAME"
    else
        echo "❌ Operação cancelada"
    fi
}

# Executar
select_node 
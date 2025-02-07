#!/bin/bash

# Variável de Namespace
NAMESPACE="${NAMESPACE:-signoz}"

# Cores para saída
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Função para exibir logs de um pod específico
get_specific_pod_logs() {
    local namespace=$1
    local pod_name=$2
    local container_name=$3

    echo -e "${YELLOW}===== LOGS DO POD: $pod_name (Container: $container_name, Namespace: $namespace) =====${NC}"

    # Verificar se o container existe no pod
    if kubectl get pod "$pod_name" -n "$namespace" -o jsonpath="{.spec.containers[*].name}" | grep -q "$container_name"; then
        kubectl logs -n "$namespace" "$pod_name" -c "$container_name" --tail=10
    else
        echo -e "${RED}Container $container_name não encontrado no pod $pod_name${NC}"
        
        # Listar containers disponíveis
        available_containers=$(kubectl get pod "$pod_name" -n "$namespace" -o jsonpath='{.spec.containers[*].name}')
        echo -e "${YELLOW}Containers disponíveis:${NC}"
        echo "$available_containers"
    fi
}

# Função para selecionar pod
select_pod() {
    local namespace=$1
    
    # Listar pods
    echo -e "${GREEN}Pods disponíveis no namespace $namespace:${NC}"
    kubectl get pods -n "$namespace" -o custom-columns=NAME:.metadata.name,STATUS:.status.phase

    # Solicitar seleção de pod
    read -p "Digite o nome do pod que deseja ver o log: " selected_pod

    # Verificar se o pod existe
    if kubectl get pod "$selected_pod" -n "$namespace" &> /dev/null; then
        # Listar containers do pod
        containers=$(kubectl get pod "$selected_pod" -n "$namespace" -o jsonpath='{.spec.containers[*].name}')
        
        # Se mais de um container, solicitar seleção
        if [ $(echo "$containers" | wc -w) -gt 1 ]; then
            echo -e "${YELLOW}Containers disponíveis:${NC}"
            echo "$containers"
            read -p "Digite o nome do container: " selected_container
        else
            # Se só um container, usar esse
            selected_container=$(echo "$containers" | awk '{print $1}')
        fi

        # Exibir logs
        get_specific_pod_logs "$namespace" "$selected_pod" "$selected_container"
    else
        echo -e "${RED}Pod não encontrado!${NC}"
    fi
}

# Função para exibir logs de um pod
get_pod_logs() {
    local namespace=$1
    local pod_name=$2
    local container_name=${3:-}

    echo -e "${YELLOW}===== LOGS DO POD: $pod_name (Namespace: $namespace) =====${NC}"

    if [ -z "$container_name" ]; then
        kubectl logs -n "$namespace" "$pod_name" --tail=100
    else
        kubectl logs -n "$namespace" "$pod_name" -c "$container_name" --tail=100
    fi
}

# Função para listar todos os pods
list_all_pods() {
    local namespace=$1
    kubectl get pods -n "$namespace" -o custom-columns=NAME:.metadata.name,STATUS:.status.phase
}

# Função principal de diagnóstico
diagnose_cluster() {
    echo -e "${GREEN}🔍 Diagnóstico de Logs no Namespace: $NAMESPACE ${NC}"
    
    # Listar pods
    echo -e "${YELLOW}Pods no Namespace $NAMESPACE:${NC}"
    list_all_pods "$NAMESPACE"

    # Coletar pods
    pods=$(kubectl get pods -n "$NAMESPACE" -o jsonpath='{.items[*].metadata.name}')

    # Iterar sobre pods
    for pod in $pods; do
        # Verificar status do pod
        status=$(kubectl get pod "$pod" -n "$NAMESPACE" -o jsonpath='{.status.phase}')
        
        if [ "$status" == "Running" ]; then
            # Obter containers do pod
            containers=$(kubectl get pod "$pod" -n "$NAMESPACE" -o jsonpath='{.spec.containers[*].name}')
            
            for container in $containers; do
                get_pod_logs "$NAMESPACE" "$pod" "$container"
            done
        else
            echo -e "${RED}Pod $pod não está em estado Running (Status: $status)${NC}"
        fi
    done
}

# Função de log detalhado para pods com erro
error_pod_logs() {
    echo -e "${RED}🚨 Pods com Erro no Namespace $NAMESPACE:${NC}"
    
    # Encontrar pods com erro
    error_pods=$(kubectl get pods -n "$NAMESPACE" | grep -E "Error|CrashLoopBackOff" | awk '{print $1}')
    
    for pod in $error_pods; do
        echo -e "${RED}Detalhes do Pod $pod:${NC}"
        kubectl describe pod "$pod" -n "$NAMESPACE"
        
        echo -e "${RED}Logs do Pod $pod:${NC}"
        kubectl logs "$pod" -n "$NAMESPACE" --tail=50
    done
}

# Menu de opções
main_menu() {
    echo "Diagnóstico de Logs - Namespace: $NAMESPACE"
    echo "Escolha uma opção:"
    echo "1. Diagnóstico Completo de Logs"
    echo "2. Logs de Pods com Erro"
    echo "3. Selecionar Pod Específico"
    echo "4. Alterar Namespace"
    echo "5. Sair"
    
    read -p "Opção: " choice
    
    case $choice in
        1) diagnose_cluster ;;
        2) error_pod_logs ;;
        3) select_pod "$NAMESPACE" ;;
        4) 
            read -p "Digite o novo namespace: " new_namespace
            export NAMESPACE="$new_namespace"
            ;;
        5) exit 0 ;;
        *) echo "Opção inválida" ;;
    esac
}

# Verificar configuração do kubectl
if ! command -v kubectl &> /dev/null; then
    echo "kubectl não encontrado. Instale o kubectl primeiro."
    exit 1
fi

# Executar menu
while true; do
    main_menu
done
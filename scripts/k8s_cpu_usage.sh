#!/bin/bash

# Função para instalar o Metrics Server
function install_metrics_server() {
    echo "Tentando instalar o Metrics Server..."
    
    # Verifica se o Metrics Server já está instalado
    if kubectl get deployment metrics-server -n kube-system &> /dev/null; then
        echo "Metrics Server já está instalado."
        return 0
    fi
    
    # Tenta instalar usando kubectl
    kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
    
    if [ $? -eq 0 ]; then
        echo "Metrics Server instalado com sucesso. Aguarde alguns minutos para inicialização."
        echo "Dica: Use 'kubectl get deployment metrics-server -n kube-system' para verificar o status."
        return 0
    else
        echo "Erro ao instalar Metrics Server. Tente instalar manualmente."
        return 1
    fi
}

# Função para exibir uso de CPU dos pods
function show_pod_cpu_usage() {
    local namespace=${1:-default}
    
    echo "Uso de CPU dos Pods no namespace: $namespace"
    echo "-------------------------------------------"
    
    # Tenta obter métricas
    local metrics_output
    metrics_output=$(kubectl top pods -n "$namespace" 2>&1)
    local metrics_exit_code=$?
    
    # Verifica se houve erro de Metrics API
    if [[ $metrics_exit_code -ne 0 ]]; then
        if [[ "$metrics_output" == *"Metrics API not available"* ]]; then
            echo "Erro: Metrics API não está disponível."
            echo "Possíveis soluções:"
            echo "1. Instalar Metrics Server"
            echo "2. Verificar configuração do cluster"
            echo ""
            read -p "Deseja tentar instalar o Metrics Server? (s/n): " install_choice
            
            if [[ "$install_choice" == "s" || "$install_choice" == "S" ]]; then
                install_metrics_server
                # Tenta novamente após instalação
                metrics_output=$(kubectl top pods -n "$namespace" 2>&1)
                metrics_exit_code=$?
            else
                return 1
            fi
        else
            echo "Erro desconhecido: $metrics_output"
            return 1
        fi
    fi
    
    # Se ainda não conseguir, sai
    if [[ $metrics_exit_code -ne 0 ]]; then
        echo "Não foi possível obter métricas de CPU."
        return 1
    fi
    
    # Cabeçalho
    printf "%-50s %-20s %-15s %-15s\n" "POD" "NAMESPACE" "CPU (cores)" "MEMORY"
    echo "-------------------------------------------"
    
    # Busca os pods e seus usos de CPU
    kubectl top pods -n "$namespace" | tail -n +2 | while read -r pod cpu mem; do
        printf "%-50s %-20s %-15s %-15s\n" "$pod" "$namespace" "$cpu" "$mem"
    done
}

# Função para converter valores de CPU e memória
function convert_cpu_value() {
    local cpu_usage="$1"
    # Remove qualquer espaço em branco
    cpu_usage=$(echo "$cpu_usage" | tr -d ' ')
    
    # Verifica se termina com 'm'
    if [[ "$cpu_usage" =~ ^[0-9]+m$ ]]; then
        # Remove o 'm' e retorna o valor
        local value="${cpu_usage%m}"
        echo "$value"
    elif [[ "$cpu_usage" =~ ^[0-9]+$ ]]; then
        # Se for um número inteiro, converte para millicores
        local value=$((cpu_usage * 1000))
        echo "$value"
    else
        # Se não for reconhecido, tenta extrair número
        local value=$(echo "$cpu_usage" | grep -oE '^[0-9]+')
        if [[ -n "$value" ]]; then
            echo "$value"
        else
            echo 0
        fi
    fi
}

function convert_memory_value() {
    local mem_usage="$1"
    # Remove qualquer espaço em branco
    mem_usage=$(echo "$mem_usage" | tr -d ' ')
    
    # Verifica se termina com 'Mi'
    if [[ "$mem_usage" =~ ^[0-9]+Mi$ ]]; then
        # Remove o 'Mi' e retorna o valor
        local value="${mem_usage%Mi}"
        echo "$value"
    elif [[ "$mem_usage" =~ ^[0-9]+$ ]]; then
        # Se for um número inteiro, assume como Mi
        echo "$mem_usage"
    else
        # Tenta extrair número
        local value=$(echo "$mem_usage" | grep -oE '^[0-9]+')
        if [[ -n "$value" ]]; then
            echo "$value"
        else
            # Se não for reconhecido, retorna 0
            echo 0
        fi
    fi
}

# Função para converter recursos de CPU para millicores
function convert_cpu_resources() {
    local cpu_resource="$1"
    
    # Remove espaços
    cpu_resource=$(echo "$cpu_resource" | tr -d ' ')
    
    # Converte diferentes formatos para millicores
    if [[ "$cpu_resource" =~ ^[0-9]+m$ ]]; then
        # Remove o 'm'
        echo "${cpu_resource%m}"
    elif [[ "$cpu_resource" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
        # Converte cores para millicores
        printf "%.0f" $(echo "$cpu_resource * 1000" | bc)
    elif [[ -z "$cpu_resource" ]]; then
        # Se estiver vazio, retorna 0
        echo 0
    else
        # Tenta extrair número
        local value=$(echo "$cpu_resource" | grep -oE '^[0-9]+')
        if [[ -n "$value" ]]; then
            echo "$value"
        else
            echo 0
        fi
    fi
}

# Função para obter recursos reservados de CPU por namespace
function get_namespace_reserved_cpu() {
    local namespace="$1"
    local total_reserved_cpu=0
    
    # Obtém lista de pods no namespace
    local pods
    pods=$(kubectl get pods -n "$namespace" -o jsonpath='{.items[*].metadata.name}')
    
    # Variável para armazenar detalhes de recursos
    local reserved_resources=""
    
    # Itera sobre cada pod
    for pod in $pods; do
        # Obtém recursos do pod usando jsonpath para maior precisão
        local pod_resources
        pod_resources=$(kubectl get pod "$pod" -n "$namespace" -o jsonpath='{.spec.containers[*].resources.requests.cpu}')
        
        # Verifica se há recursos definidos
        if [[ -n "$pod_resources" ]]; then
            # Converte para millicores
            local cpu_millicores
            cpu_millicores=$(convert_cpu_resources "$pod_resources")
            
            # Soma ao total
            total_reserved_cpu=$((total_reserved_cpu + cpu_millicores))
            
            # Adiciona aos recursos detalhados
            reserved_resources+="$pod: $pod_resources (${cpu_millicores}m)\n"
        fi
    done
    
    # Retorna o total de recursos reservados
    echo "$total_reserved_cpu"
}

# Função para mostrar uso de CPU de todos os namespaces
function show_all_namespaces_cpu_usage() {
    echo "Uso de CPU em todos os namespaces do cluster"
    echo "=========================================="
    
    # Obtém o nome do cluster atual
    local cluster_name
    cluster_name=$(kubectl config current-context)
    echo "Cluster: $cluster_name"
    echo "Data/Hora: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""
    
    # Variáveis para armazenar totais
    local total_cpu_usage=0
    local total_memory_usage=0
    local total_reserved_cpu=0
    local namespace_count=0

    # Cria um arquivo temporário para armazenar resultados
    local temp_file=$(mktemp)
    local reserved_cpu_file=$(mktemp)
    
    # Lista todos os namespaces
    kubectl get namespaces -o jsonpath='{.items[*].metadata.name}' | tr ' ' '\n' | while read -r namespace; do
        # Pula namespaces vazios ou de sistema que não interessam
        if [[ -z "$namespace" || "$namespace" == "kube-system" || "$namespace" == "kube-public" || "$namespace" == "kube-node-lease" ]]; then
            continue
        fi
        
        # Incrementa contador de namespaces
        ((namespace_count++))
        
        echo "Namespace: $namespace"
        echo "-------------------------------------------"
        
        # Variáveis para armazenar uso de CPU e memória do namespace
        local namespace_cpu_total=0
        local namespace_memory_total=0
        
        # Obtém recursos reservados de CPU
        local namespace_reserved_cpu
        namespace_reserved_cpu=$(get_namespace_reserved_cpu "$namespace")
        
        # Chama a função de uso de CPU para o namespace específico e captura a saída
        local namespace_metrics
        namespace_metrics=$(kubectl top pods -n "$namespace" 2>/dev/null)
        
        if [[ -n "$namespace_metrics" ]]; then
            # Processa as métricas do namespace
            local pod cpu_usage mem_usage
            while IFS=' ' read -r pod cpu_usage mem_usage; do
                # Pula o cabeçalho se existir
                [[ "$pod" == "NAME" ]] && continue
                
                printf "%-50s %-20s %-15s %-15s\n" "$pod" "$namespace" "$cpu_usage" "$mem_usage"
                
                # Converte valores de CPU e memória
                local cpu_value=$(convert_cpu_value "$cpu_usage")
                local mem_value=$(convert_memory_value "$mem_usage")
                
                # Soma os valores
                namespace_cpu_total=$((namespace_cpu_total + cpu_value))
                namespace_memory_total=$((namespace_memory_total + mem_value))
            done <<< "$namespace_metrics"
            
            # Salva resultados no arquivo temporário
            printf "%s\t%d\t%d\n" "$namespace" "$namespace_cpu_total" "$namespace_memory_total" >> "$temp_file"
            printf "%s\t%d\n" "$namespace" "$namespace_reserved_cpu" >> "$reserved_cpu_file"
            
            # Mostra total do namespace
            printf "\nTotal do namespace %s: CPU: %sm, Memória: %sMi\n" "$namespace" "$namespace_cpu_total" "$namespace_memory_total"
            
            # Mostra recursos reservados apenas se houver
            if [[ "$namespace_reserved_cpu" -gt 0 ]]; then
                printf "Total reservado de CPU: %sm\n\n" "$namespace_reserved_cpu"
            fi
        else
            echo "Sem métricas disponíveis para este namespace."
            echo ""
        fi
    done
    
    # Calcula totais a partir dos arquivos temporários
    if [[ -f "$temp_file" ]]; then
        total_cpu_usage=$(awk '{sum += $2} END {print sum}' "$temp_file")
        total_memory_usage=$(awk '{sum += $3} END {print sum}' "$temp_file")
        total_reserved_cpu=$(awk '{sum += $2} END {print sum}' "$reserved_cpu_file")
        
        # Mostra total de namespaces processados e uso total
        echo "=========================================="
        echo "Resumo do Cluster:"
        echo "Total de namespaces processados: $namespace_count"
        printf "Uso total de CPU: %sm\n" "$total_cpu_usage"
        printf "Uso total de Memória: %sMi\n" "$total_memory_usage"
        printf "Total de CPU reservada: %sm\n" "$total_reserved_cpu"
        
        # Remove os arquivos temporários
        rm "$temp_file"
        rm "$reserved_cpu_file"
    else
        echo "Nenhum namespace processado."
    fi
}

# Verifica se o kubectl está instalado
if ! command -v kubectl &> /dev/null; then
    echo "Erro: kubectl não está instalado."
    exit 1
fi

# Verifica se está conectado a algum cluster
if ! kubectl cluster-info &> /dev/null; then
    echo "Erro: Não está conectado a nenhum cluster Kubernetes."
    exit 1
fi

# Opções de execução
case "$1" in
    "--all")
        show_all_namespaces_cpu_usage
        ;;
    "--namespace")
        if [ -z "$2" ]; then
            echo "Por favor, especifique o namespace."
            echo "Uso: $0 --namespace NAMESPACE_NAME"
            exit 1
        fi
        show_pod_cpu_usage "$2"
        ;;
    *)
        show_pod_cpu_usage
        ;;
esac 
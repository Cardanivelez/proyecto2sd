#!/bin/bash

# Configuración de las instancias
NAMENODE_HOST="172.31.1.10"
DATANODE1_HOST="172.31.1.11"
DATANODE2_HOST="172.31.1.12"
DATANODE3_HOST="172.31.1.13"
SSH_KEY="~/path/to/your/key.pem"
DFS_USER="ubuntu"  # o el usuario que uses en tus instancias

# Función para desplegar en una instancia
deploy_instance() {
    local host=$1
    local type=$2
    local node_id=$3
    
    echo "Desplegando $type en $host..."
    
    # Copiar archivos al servidor
    ssh -i $SSH_KEY $DFS_USER@$host "mkdir -p ~/dfs"
    scp -i $SSH_KEY -r ../src ../config ../scripts $DFS_USER@$host:~/dfs/
    
    # Configurar y ejecutar el servicio
    ssh -i $SSH_KEY $DFS_USER@$host "
        cd ~/dfs
        
        # Instalar dependencias
        sudo apt-get update
        sudo apt-get install -y python3-pip
        pip3 install poetry
        
        # Configurar el proyecto
        poetry install
        
        # Generar código gRPC
        ./scripts/generate_grpc.sh
        
        # Crear directorio de datos
        sudo mkdir -p /data/$type
        sudo chown -R $DFS_USER:$DFS_USER /data/$type
        
        # Crear servicio systemd
        sudo tee /etc/systemd/system/dfs-$type.service <<EOF
[Unit]
Description=DFS $type
After=network.target

[Service]
Type=simple
User=$DFS_USER
WorkingDirectory=/home/$DFS_USER/dfs
Environment=DFS_CONFIG=/home/$DFS_USER/dfs/config/cluster_config.yaml
ExecStart=$(which poetry) run dfs-$type $([ ! -z "$node_id" ] && echo "--node-id $node_id")
Restart=always

[Install]
WantedBy=multi-user.target
EOF
        
        # Iniciar el servicio
        sudo systemctl daemon-reload
        sudo systemctl enable dfs-$type
        sudo systemctl start dfs-$type
    "
}

# Desplegar NameNode
deploy_instance $NAMENODE_HOST "namenode"

# Desplegar DataNodes
deploy_instance $DATANODE1_HOST "datanode" "datanode1"
deploy_instance $DATANODE2_HOST "datanode" "datanode2"
deploy_instance $DATANODE3_HOST "datanode" "datanode3"

echo "Despliegue completado!"
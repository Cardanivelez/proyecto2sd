#!/bin/bash

# Configuración de las instancias
NAMENODE_HOST="34.202.250.249"
DATANODE1_HOST="3.232.66.23"
DATANODE2_HOST="44.208.230.35"
DATANODE3_HOST="54.235.162.161"
SSH_KEY="C:\Users\Danilo\Desktop\semestre 7 (2025-1)\Arquitectura De Nube Y SD\Proyecto2\proyecto2.pem" 
DFS_USER="ubuntu"

# Ruta del entorno virtual en la instancia remota
VENV_PATH="/home/$DFS_USER/dfs/venv"

# Función para desplegar en una instancia
deploy_instance() {
    local host=$1
    local type=$2
    local node_id=$3

    echo "Desplegando $type en $host..."

    # Copiar archivos al servidor
    ssh -i $SSH_KEY $DFS_USER@$host "mkdir -p ~/dfs"
    scp -i $SSH_KEY -r ../src ../config ../scripts ../requirements.txt $DFS_USER@$host:~/dfs/

    # Configurar y ejecutar el servicio
    ssh -i $SSH_KEY $DFS_USER@$host "
        cd ~/dfs

        # Instalar dependencias del sistema
        sudo apt-get update
        sudo apt-get install -y python3-pip python3-venv

        # Crear entorno virtual si no existe
        if [ ! -d 'venv' ]; then
            python3 -m venv venv
        fi

        # Activar entorno virtual e instalar dependencias
        source venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt

        # Generar código gRPC si es necesario
        if [ -f ./scripts/generate_grpc.sh ]; then
            chmod +x ./scripts/generate_grpc.sh
            ./scripts/generate_grpc.sh
        fi

        # Crear directorio de datos para DataNodes
        if [ \"$type\" = \"datanode\" ]; then
            mkdir -p ~/dfs/data/$node_id
        fi

        # Crear servicio systemd
        SERVICE_PATH=\"/etc/systemd/system/dfs-$type${node_id:+-$node_id}.service\"
        EXEC_CMD=\"source $VENV_PATH/bin/activate && python3 src/$type/server.py\"
        if [ \"$type\" = \"datanode\" ]; then
            EXEC_CMD=\"\$EXEC_CMD --node-id $node_id --storage ~/dfs/data/$node_id\"
        fi

        sudo bash -c 'cat > \$SERVICE_PATH' <<EOF
[Unit]
Description=DFS $type $node_id
After=network.target

[Service]
Type=simple
User=$DFS_USER
WorkingDirectory=/home/$DFS_USER/dfs
ExecStart=/bin/bash -c \"$EXEC_CMD\"
Restart=always

[Install]
WantedBy=multi-user.target
EOF

        # Iniciar el servicio
        sudo systemctl daemon-reload
        sudo systemctl enable dfs-$type${node_id:+-$node_id}
        sudo systemctl restart dfs-$type${node_id:+-$node_id}
    "
}

# Desplegar NameNode
deploy_instance $NAMENODE_HOST "namenode"

# Desplegar DataNodes
deploy_instance $DATANODE1_HOST "datanode" "datanode1"
deploy_instance $DATANODE2_HOST "datanode" "datanode2"
deploy_instance $DATANODE3_HOST "datanode" "datanode3"

echo "Despliegue completado!"
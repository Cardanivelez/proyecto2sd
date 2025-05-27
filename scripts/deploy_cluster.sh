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

    # Copiar archivos al servidor (ahora solo clona el repo)
    ssh -i $SSH_KEY $DFS_USER@$host "rm -rf ~/proyecto2sd && git clone https://github.com/Cardanivelez/proyecto2sd.git"

    # Configurar y ejecutar el servicio
    ssh -i $SSH_KEY $DFS_USER@$host "
        cd ~/proyecto2sd

        # Crear entorno virtual Python 3.11 si no existe
        if [ ! -d 'env' ]; then
            python3.11 -m venv env
        fi

        # Activar entorno virtual e instalar dependencias
        source env/bin/activate
        python3 -m pip install --upgrade pip setuptools wheel
        pip install -r requirements.txt

        # Generar código gRPC si es necesario
        if [ -f ./scripts/generate_grpc.sh ]; then
            chmod +x ./scripts/generate_grpc.sh
            ./scripts/generate_grpc.sh
        fi

        # Crear directorio de datos para DataNodes
        if [ \"$type\" = \"datanode\" ]; then
            mkdir -p ~/proyecto2sd/data/$node_id
        fi

        # Crear servicio systemd
        SERVICE_PATH="/etc/systemd/system/dfs-$type${node_id:+-$node_id}.service"
        EXEC_CMD="source /home/$DFS_USER/proyecto2sd/env/bin/activate && python3 src/$type/server.py"
        if [ \"$type\" = \"datanode\" ]; then
            EXEC_CMD=\"$EXEC_CMD --node-id $node_id --storage ~/proyecto2sd/data/$node_id\"
        fi

        sudo bash -c 'cat > $SERVICE_PATH' <<EOF
[Unit]
Description=DFS $type $node_id
After=network.target

[Service]
Type=simple
User=$DFS_USER
WorkingDirectory=/home/$DFS_USER/proyecto2sd
ExecStart=/bin/bash -c "$EXEC_CMD"
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
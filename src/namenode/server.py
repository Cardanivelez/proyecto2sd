from fastapi import FastAPI, HTTPException
from typing import Dict, List
import uvicorn
import uuid
import random
import aiohttp
import asyncio
import argparse
import json
from ..common.config import Config

PERSISTENCE_FILE = "namenode_state.json"

def save_state(self):
    state = {
        "files": self.files,
        "directory_structure": self.directory_structure
    }
    with open(PERSISTENCE_FILE, "w") as f:
        json.dump(state, f)

def load_state(self):
    try:
        with open(PERSISTENCE_FILE, "r") as f:
            state = json.load(f)
            self.files = state.get("files", {})
            self.directory_structure = state.get("directory_structure", {"/": {}})
    except Exception:
        self.files = {}
        self.directory_structure = {"/": {}}

class NameNode:
    def __init__(self):
        self.files: Dict[str, dict] = {}
        self.datanodes = {
            "datanode1": {"host": "3.232.66.23", "port": 50051, "load": 0},
            "datanode2": {"host": "44.208.230.35", "port": 50052, "load": 0},
            "datanode3": {"host": "54.235.162.161", "port": 50053, "load": 0}
        }
        self.block_size = 64 * 1024 * 1024
        self.replication_factor = 2
        self.directory_structure = {"/": {}}
        load_state(self)

    async def select_optimal_datanodes(self, file_size: int) -> List[dict]:
        """Selecciona los DataNodes óptimos basado en carga y disponibilidad"""
        available_nodes = []
        
        # Obtener métricas de cada DataNode
        for node_id, node_info in self.datanodes.items():
            try:
                metrics_port = node_info['port'] + 100  # Usar puerto de métricas
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"http://{node_info['host']}:{metrics_port}/metrics") as response:
                        metrics = await response.json()
                        available_nodes.append({
                            "node_id": node_id,
                            "load": metrics["load"],
                            "available_space": metrics["available_space"],
                            "latency": metrics["latency"]
                        })
            except Exception as e:
                print(f"Error getting metrics from {node_id}: {e}")

        # Ordenar por menor carga y mayor espacio disponible
        available_nodes.sort(key=lambda x: (x["load"], -x["available_space"]))
        
        # Seleccionar los mejores nodos para replicación
        selected_nodes = available_nodes[:self.replication_factor]
        return selected_nodes

    async def allocate_blocks(self, file_size: int) -> List[dict]:
        """Asigna bloques a DataNodes óptimos"""
        num_blocks = (file_size + self.block_size - 1) // self.block_size
        blocks = []
        
        for _ in range(num_blocks):
            block_id = str(uuid.uuid4())
            selected_nodes = await self.select_optimal_datanodes(file_size)
            if not selected_nodes:
                raise HTTPException(status_code=500, detail="No hay DataNodes disponibles para almacenar bloques. Verifica que los DataNodes estén activos y accesibles.")
            
            # Designar leader y followers
            leader = selected_nodes[0]
            followers = selected_nodes[1:]
            
            blocks.append({
                "block_id": block_id,
                "leader": {
                    "node_id": leader["node_id"],
                    "address": f"{self.datanodes[leader['node_id']]['host']}:{self.datanodes[leader['node_id']]['port']}"
                },
                "followers": [{
                    "node_id": node["node_id"],
                    "address": f"{self.datanodes[node['node_id']]['host']}:{self.datanodes[node['node_id']]['port']}"
                } for node in followers]
            })
        
        return blocks

    def update_directory_structure(self, path: str, is_directory: bool = False):
        """Actualiza la estructura de directorios"""
        current = self.directory_structure
        parts = path.strip('/').split('/')
        
        for i, part in enumerate(parts):
            if i == len(parts) - 1 and not is_directory:
                current[part] = "file"
            else:
                if part not in current:
                    current[part] = {}
                current = current[part]
        save_state(self)

async def run_server(host: str, port: int, config_path: str = None):
    """Inicia el servidor FastAPI del NameNode"""
    # Cargar configuración
    config = Config.load(config_path)
    
    # Crear instancia del NameNode
    namenode = NameNode()
    
    # Configurar FastAPI
    app = FastAPI(title="NameNode API")
    
    # Agregar rutas
    @app.post("/files")
    async def create_file(filename: str, size: int):
        if filename in namenode.files:
            raise HTTPException(status_code=400, detail="File already exists")
        
        blocks = await namenode.allocate_blocks(size)
        namenode.files[filename] = {
            "size": size,
            "blocks": blocks
        }
        namenode.update_directory_structure(filename)
        save_state(namenode)
        return {"filename": filename, "blocks": blocks}

    @app.post("/directory")
    async def create_directory(path: str):
        namenode.update_directory_structure(path, is_directory=True)
        save_state(namenode)
        return {"message": f"Directory {path} created"}

    @app.get("/ls/{path:path}")
    async def list_directory(path: str):
        current = namenode.directory_structure
        for part in path.strip('/').split('/'):
            if part:
                if part not in current:
                    raise HTTPException(status_code=404, detail="Path not found")
                current = current[part]
        return {"contents": current}
    
    @app.delete("/directory")
    async def delete_directory(path: str):
        # Navegar hasta el directorio padre
        current = namenode.directory_structure
        parts = path.strip('/').split('/')
        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                # Eliminar el directorio si existe
                if part in current and isinstance(current[part], dict):
                    del current[part]
                    save_state(namenode)
                    return {"message": f"Directorio {path} eliminado"}
                else:
                    raise HTTPException(status_code=404, detail="Directorio no encontrado")
            if part not in current or not isinstance(current[part], dict):
                raise HTTPException(status_code=404, detail="Ruta no encontrada")
            current = current[part]
    
    # Iniciar servidor
    config = uvicorn.Config(app, host=host, port=port)
    server = uvicorn.Server(config)
    await server.serve()

def main():
    """Punto de entrada principal para el NameNode"""
    parser = argparse.ArgumentParser(description='NameNode Server')
    parser.add_argument('--host', default="0.0.0.0", help='Host address to bind to')
    parser.add_argument('--port', type=int, required=True, help='Port to listen on')
    parser.add_argument('--config', help='Path to configuration file')
    
    args = parser.parse_args()
    
    # Iniciar el servidor
    asyncio.run(run_server(args.host, args.port, args.config))

if __name__ == "__main__":
    main()
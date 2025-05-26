from fastapi import FastAPI, HTTPException
from typing import Dict, List
import uvicorn
import uuid
import random
import aiohttp
import asyncio

class NameNode:
    def __init__(self):
        self.files: Dict[str, dict] = {}
        self.datanodes = {
            "datanode1": {"host": "172.31.1.11", "port": 50051, "load": 0},
            "datanode2": {"host": "172.31.1.12", "port": 50051, "load": 0},
            "datanode3": {"host": "172.31.1.13", "port": 50051, "load": 0}
        }
        self.block_size = 64 * 1024 * 1024
        self.replication_factor = 2
        self.directory_structure = {"/" : {}}

    async def select_optimal_datanodes(self, file_size: int) -> List[dict]:
        """Selecciona los DataNodes óptimos basado en carga y disponibilidad"""
        available_nodes = []
        
        # Obtener métricas de cada DataNode
        for node_id, node_info in self.datanodes.items():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"http://{node_info['host']}:{node_info['port']}/metrics") as response:
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

app = FastAPI()
namenode = NameNode()

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
    return {"filename": filename, "blocks": blocks}

@app.post("/directory")
async def create_directory(path: str):
    namenode.update_directory_structure(path, is_directory=True)
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
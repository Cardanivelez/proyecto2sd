import grpc
from concurrent import futures
from pathlib import Path
import asyncio
from ..proto import dfs_pb2, dfs_pb2_grpc
import psutil
import time
from fastapi import FastAPI
import random 
from typing import List 

class DataNode(dfs_pb2_grpc.FileServiceServicer):
    def __init__(self, node_id: str, storage_path: str = "./storage"):
        self.node_id = node_id
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.leader_blocks = set()  # Bloques para los que este nodo es leader
        self.follower_blocks = set()  # Bloques para los que este nodo es follower
        self.metrics_app = FastAPI()
        self.setup_metrics_endpoint()

    def setup_metrics_endpoint(self):
        @self.metrics_app.get("/metrics")
        async def get_metrics():
            return {
                "load": psutil.cpu_percent(),
                "available_space": psutil.disk_usage(str(self.storage_path)).free,
                "latency": self.get_network_latency()
            }

    def get_network_latency(self):
        # Simulación simple de latencia
        return random.uniform(0.1, 2.0)

    async def become_leader(self, block_id: str, follower_nodes: List[str]):
        """Gestiona el rol de leader para un bloque"""
        self.leader_blocks.add(block_id)
        
        # Coordinar con followers
        for follower in follower_nodes:
            try:
                channel = grpc.aio.insecure_channel(follower)
                stub = dfs_pb2_grpc.FileServiceStub(channel)
                
                # Enviar datos a follower
                block_path = self.storage_path / block_id
                with open(block_path, 'rb') as f:
                    while chunk := f.read(1024 * 1024):
                        await stub.ReplicateBlock(
                            dfs_pb2.BlockData(
                                block_id=block_id,
                                data=chunk,
                                source_node=self.node_id
                            )
                        )
            except Exception as e:
                print(f"Error replicating to follower {follower}: {e}")
                # Implementar reintentos o selección de follower alternativo

    async def PutBlock(self, request_iterator, context):
        """Maneja la escritura de bloques y coordina la replicación"""
        block_data = b""
        block_id = None
        replica_nodes = []
        
        async for request in request_iterator:
            if block_id is None:
                block_id = request.block_id
                replica_nodes = request.replica_nodes
            block_data += request.data

        if block_id:
            # Guardar bloque localmente
            block_path = self.storage_path / block_id
            with open(block_path, 'wb') as f:
                f.write(block_data)
            
            # Si es leader, coordinar replicación
            if self.node_id == replica_nodes[0]:
                await self.become_leader(block_id, replica_nodes[1:])
            
            return dfs_pb2.BlockResponse(success=True)
        
        return dfs_pb2.BlockResponse(success=False, message="No block ID provided")
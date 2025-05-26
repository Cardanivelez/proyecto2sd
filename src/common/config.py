from dataclasses import dataclass
from typing import Dict, Optional
import yaml
import os

@dataclass
class Config:
    """Configuración global del sistema"""
    
    def __init__(self, config_path: str = None):
        # Valores por defecto
        self.NAMENODE_HOST = "localhost"
        self.NAMENODE_PORT = 8000
        self.DATANODES = {}
        self.REPLICATION_FACTOR = 2
        self.BLOCK_SIZE = 64 * 1024 * 1024  # 64MB
        
        # Cargar configuración si existe
        if config_path and os.path.exists(config_path):
            self.load_from_yaml(config_path)
    
    def load_from_yaml(self, config_path: str):
        """Carga la configuración desde un archivo YAML"""
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        # Configuración del NameNode
        if 'namenode' in config:
            self.NAMENODE_HOST = config['namenode']['host']
            self.NAMENODE_PORT = config['namenode']['port']
        
        # Configuración de DataNodes
        if 'datanodes' in config:
            self.DATANODES = {
                node_id: f"{node_info['host']}:{node_info['port']}"
                for node_id, node_info in config['datanodes'].items()
            }
        
        # Configuración de replicación
        if 'replication' in config:
            self.REPLICATION_FACTOR = config['replication']['factor']
            self.BLOCK_SIZE = config['replication']['block_size']

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> 'Config':
        """Carga la configuración desde un archivo"""
        if not config_path:
            config_path = os.getenv('DFS_CONFIG', 'config/cluster_config.yaml')
        return cls(config_path)
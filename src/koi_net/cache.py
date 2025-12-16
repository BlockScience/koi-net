import os
import shutil
from rid_lib.core import RID, RIDType
from rid_lib.ext import Bundle
from rid_lib.ext.utils import b64_encode, b64_decode

from .config.base import BaseNodeConfig


class Cache:
    def __init__(self, config: BaseNodeConfig):
        self.config = config
        
    @property
    def directory_path(self):
        return self.config.koi_net.cache_directory_path
        
    def file_path_to(self, rid: RID) -> str:
        encoded_rid_str = b64_encode(str(rid))
        return f"{self.directory_path}/{encoded_rid_str}.json"

    def write(self, bundle: Bundle) -> Bundle:
        """Writes bundle to cache, returns a Bundle."""
        if not os.path.exists(self.directory_path):
            os.makedirs(self.directory_path)
            
        with open(
            file=self.file_path_to(bundle.manifest.rid), 
            mode="w", 
            encoding="utf-8"
        ) as f:
            f.write(bundle.model_dump_json(indent=2))

        return bundle
    
    def exists(self, rid: RID) -> bool:
        return os.path.exists(
            self.file_path_to(rid)
        )

    def read(self, rid: RID) -> Bundle | None:
        """Reads and returns CacheEntry from RID cache."""
        try:
            with open(
                file=self.file_path_to(rid), 
                mode="r",
                encoding="utf-8"
            ) as f:
                return Bundle.model_validate_json(f.read())
        except FileNotFoundError:
            return None
    
    def list_rids(self, rid_types: list[RIDType] | None = None) -> list[RID]:
        if not os.path.exists(self.directory_path):
            return []
        
        rids = []
        for filename in os.listdir(self.directory_path):
            encoded_rid_str = filename.split(".")[0]
            rid_str = b64_decode(encoded_rid_str)
            rid = RID.from_string(rid_str)
            
            if not rid_types or type(rid) in rid_types:
                rids.append(rid)
            
        return rids
                
    def delete(self, rid: RID) -> None:
        """Deletes cache bundle."""
        try:
            os.remove(self.file_path_to(rid))
        except FileNotFoundError:
            return

    def drop(self) -> None:
        """Deletes all cache bundles."""
        try:
            shutil.rmtree(self.directory_path)
        except FileNotFoundError:
            return


from pydantic import BaseModel, Field, PrivateAttr
from ruamel.yaml import YAML


class KoiNetworkConfig(BaseModel):
    nodes: dict[str, str] = Field(default_factory=dict)
    _file_path: str = PrivateAttr(default="koi-net-config.yaml")

    @classmethod
    def load_from_yaml(
        cls, 
        file_path: str = "koi-net-config.yaml", 
    ):
        yaml = YAML()
        
        try:
            with open(file_path, "r") as f:
                file_content = f.read()
            config_data = yaml.load(file_content)
            config = cls.model_validate(config_data)
            
        except FileNotFoundError:
            config = cls()
        
        config._file_path = file_path
        config.save_to_yaml()
        return config
    
    def save_to_yaml(self):
        yaml = YAML()
        
        with open(self._file_path, "w") as f:
            try:
                config_data = self.model_dump(mode="json")
                yaml.dump(config_data, f)
            except Exception as e:
                if self._file_content:
                    f.seek(0)
                    f.truncate()
                    f.write(self._file_content)
                raise e
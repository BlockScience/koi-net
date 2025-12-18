class KoiNetCliError(Exception):
    ...

class MissingEnvVariablesError(KoiNetCliError):
    def __init__(self, message: str, vars: list[str]):
        super().__init__(message)
        self.vars = vars
        
class NodeExistsError(KoiNetCliError):
    ...
    
class NodeNotFoundError(KoiNetCliError):
    ...
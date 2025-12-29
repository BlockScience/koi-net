from koi_net.exceptions import KoiNetError


class KoiNetCliError(KoiNetError):
    pass

class MissingEnvVariablesError(KoiNetCliError):
    def __init__(self, message: str, vars: list[str]):
        super().__init__(message)
        self.vars = vars
        
class LocalNodeExistsError(KoiNetCliError):
    pass
    
class LocalNodeNotFoundError(KoiNetCliError):
    pass
    
class ModuleNotFoundError(KoiNetCliError):
    pass

class MultipleEntrypointError(KoiNetCliError):
    pass
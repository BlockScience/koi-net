from koi_net.exceptions import KoiNetError


class KoiNetCliError(KoiNetError):
    pass
        
class LocalNodeExistsError(KoiNetCliError):
    pass
    
class LocalNodeNotFoundError(KoiNetCliError):
    pass
    
class ModuleNotFoundError(KoiNetCliError):
    pass

class MultipleEntrypointError(KoiNetCliError):
    pass
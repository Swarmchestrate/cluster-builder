import jinja2

def create():

    """
    Create a new k3s cluster with OpenTofu
    """
    
    substitute_values()

    deploy()

    configure()


def substitute_values():
    """
    Function to substitute values in the opentofu configuration file
    """
    
    raise NotImplementedError


def deploy():
    """
    Function to deploy the infrastructure
    """
    
    raise NotImplementedError

def configure():
    """
    Function to configure the k3s cluster
    """
    
    raise NotImplementedError
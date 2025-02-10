aws_config = {
    "cloud": "aws",
    "aws_region": "eu-west-2",   # London region
    "instance_type": "t2.micro",
    "ssh_key_name": "g",           # AWS key pair name  
    "k3s_token": "test",
    "ami": "ami-0c0493bbac867d427",
    "aws_ha_server_count": 0,
    "aws_worker_count": 0,
    "aws_access_key": "YOUR_AWS_ACCESS_KEY",
    "aws_secret_key": "YOUR_AWS_SECRET_KEY"
}

openstack_config = {
    "cloud": "openstack",
    "auth_type": "v3applicationcredential",
    "auth_url": "auth_url",
    "application_credential_id": "app_cred_id",
    "application_credential_secret": "secret",
    "project_name": "SwarmChestrate",
    "region": "RegionOne",
    "image_id": "b2be6f4e-ebd8-42af-a526-63691a4d90ea",
    "flavor_id": "m2.small",
    "ssh_key_name": "g",
    "openstack_worker_count": 0,
    "openstack_ha_server_count": 0,
    "k3s_token": "test"
}
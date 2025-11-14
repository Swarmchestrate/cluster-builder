# aws example:

```python
config = {
    "cloud": "aws",
    "k3s_role": "master", # could be master or worker
    "ha": false,
    "instance_type": "t2.small",
    "ssh_user": "ec2-user",
    "ssh_key": "/path/to/key.pem",
    "ami": "ami-0c0493bbac867d427",
    // If existing SG is specified, it will be used directly with no port changes
    "security_group_id": "sg-0123456789abcdef0",
    // No security_group_id means a new SG will be created and these ports applied as rules
    // These ports will be used ONLY if creating a new SG
    "custom_ingress_ports": [
        {
            "from": 10020,
            "to": 10025,
            "protocol": "tcp",
            "source": "0.0.0.0/0"
        },
        {
            "from": 1003,
            "to": 1003,
            "protocol": "udp",
            "source": "10.0.0.0/16"
        }
    ],
    "custom_egress_ports": [
        {
            "from": 10020,
            "to": 10025,
            "protocol": "tcp",
            "destination": "0.0.0.0/0"
        }
        ]
}
```

# openstack example:

```python
config = {
      "cloud": "openstack",
      "openstack_image_id": "b2be6f4e-ebd8-42af-a526-63691a4d90ea",
      "openstack_flavor_id": "m2.small",
      "volume_size": "10",
      "k3s_role": "worker",  # could be master or worker
      "ha": false,
      "ssh_user": "ubuntu",
      "ssh_key": "/path/to/key.pem",
      "floating_ip_pool": "ext-net",
      "network_id": "bbe042e4-91a1-4601-962f-14a31e5e2787",
      "use_block_device": true,
      // If existing SG is specified, it will be used directly with no port changes
      "security_group_id": "f05b97f0-140a-4d24-bfc6-3a197e842739",
      // No security_group_id means a new SG will be created and these ports applied as rules
      // These ports will be used ONLY if creating a new SG
      "custom_ingress_ports": [
          {
              "from": 10020,
              "to": 10025,
              "protocol": "tcp",
              "source": "0.0.0.0/0"
          },
          {
              "from": 1003,
              "to": 1003,
              "protocol": "udp",
              "source": "10.0.0.0/16"
          }
      ],
      "custom_egress_ports": [
          {
              "from": 10020,
              "to": 10025,
              "protocol": "tcp",
              "destination": "0.0.0.0/0"
          }
          ]
      }
```

# edge example:

```python
config = {
    "cloud": "edge",
    "edge_device_ip": "10.0.0.1",
    "ssh_user": "your_user",
    "ssh_auth_method": "key",  # "password" or "key"
    "ssh_key": "/path/to/key.pem",  # required if ssh_auth_method == "key"
    # "ssh_password": "your_password",  # required if ssh_auth_method == "password"
    "k3s_token": "testtoken",
    "k3s_role": "worker", # could be master or worker
    "ha": False, # need this one only for master
    }
```
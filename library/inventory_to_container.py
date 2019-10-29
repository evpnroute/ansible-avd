#!/usr/bin/env python
# -*- coding: utf-8 -*-
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.connection import Connection, ConnectionError

import json
import yaml
import pprint
from treelib import Node, Tree
from ansible.parsing.dataloader import DataLoader
from ansible.vars.manager import VariableManager
from ansible.inventory.manager import InventoryManager

def isIterable( testing_object= None):
    """
    Test if an object is iterable or not.

    Test if an object is iterable or not. If yes return True, else return False.

    Parameters
    ----------
    testing_object : any, optional
        Object to test if it is iterable or not, by default None
    """
    try:
        some_object_iterator = iter(testing_object)
        return True
    except TypeError as te:
        return False


def serialize(dict_inventory, parent_container=None, tree_topology=None):
    if isIterable(dict_inventory):
        # Working with ROOT container for Fabric
        if tree_topology is None:
            # initiate tree topology and add ROOT under Tenant
            tree_topology = Tree()
            tree_topology.create_node("Tenant", "Tenant")
            parent_container = 'Tenant'

        # Recursive Inventory read
        for k1, v1 in dict_inventory.items():
            # Read a leaf
            if isIterable(v1) and 'children' not in v1 :
                tree_topology.create_node(k1, k1, parent=parent_container)
            # If subgroup has kids
            if isIterable(v1) and 'children' in v1:
                tree_topology.create_node(k1, k1, parent=parent_container)
                serialize(
                    dict_inventory=v1['children'],
                    parent_container=k1,
                    tree_topology=tree_topology
                )
            elif k1 == 'children' and isIterable(v1):
                # Extract sub-group information
                for k2, v2 in v1.items():
                    # Add subgroup to tree
                    tree_topology.create_node(k2, k2, parent=parent_container)
                    serialize(
                        dict_inventory=v2,
                        parent_container=k2,
                        tree_topology=tree_topology
                    )
            # elif 'hosts' in v1 and 'children' not in v1:
            #     tree_topology.create_node(k1, k1, parent=parent_container)
        return tree_topology


if __name__ == '__main__':

    """ main entry point for module execution
    """
    argument_spec = dict(
        inventory=dict(type='str', required=True),
        container_root=dict(type='str', required=True),
        destination=dict(type='str', required=True)
    )

    module = AnsibleModule(argument_spec=argument_spec,
                           supports_check_mode=False)
    result = dict(changed=False, inventory_to_cv_topology={})

    # "/Users/tgrimonet/Projects/ansible-devel/github/aristanetworks/upstream-ansible-avd/examples/evpn-l3ls-cvp-deployment/inventory.yml"
    inventory_file = module.params['inventory']
    parent_container = module.params['container_root']

    inventory_content = str()
    with open(inventory_file, 'r') as stream:
        try:
            inventory_content = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    serialized_inventory = serialize(dict_inventory=inventory_content)
    # print '** Complete Inventory tree'
    # print serialized_inventory.show()
    tree_dc = serialized_inventory.subtree(parent_container)
    # print '** Partial Inventory tree starting from ' + parent_container
    # print tree_dc.show()
    container_list = [tree_dc[node].tag for node in tree_dc.expand_tree()]

    container_json = {}
    for container in container_list:
        data = dict()
        if container != 'Tenant':
            parent = serialized_inventory.parent(container)
            if container == parent_container:
                data['parent_container'] = 'Tenant'
            elif parent.tag != 'Tenant':
                data['parent_container'] = parent.tag
            container_json[container] = data

    result['inventory_to_cv_topology']['CVP_TOPOLOGY'] = container_json
    with open(module.params['destination'], 'w') as file:
        documents = yaml.dump(result['inventory_to_cv_topology'], file)
    module.exit_json(**result)

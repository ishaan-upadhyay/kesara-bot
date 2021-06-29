# Least-recently used cache implementation as written by Jerry An 
# https://levelup.gitconnected.com/design-an-least-recently-used-cache-in-python-2f2d4a3fee6d

class Node:
    def __init__(self, key, value) -> None:
        self.key = key
        self.val = value
        self.next = None
        self.prev = None
    
class LRUCache:
    """Implementation of a least recently used cache in Python using a doubly-linked list alongside a hashmap

    :param capacity: Size of the cache
    """
    
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.search = {}
        self.dummy = Node(0,0)
        self.head = self.dummy.next
        self.tail = self.dummy.next
             
    def remove_head(self):
        """Remove the head node (least recently used)
        """
        if not self.head:
            return
        prev = self.head
        self.head = self.head.next
        if self.head:
            self.head.prev = None
        del prev
        
    def append_new_node(self, new_node):
        """Adds the new node to the tail (most recently used)

        :param new_node: Node (key-value pair) to be added to the cache
        :type: Node
        """
        if not self.tail:
            self.head = self.tail = new_node
        else:
            self.tail.next = new_node
            new_node.prev = self.tail
            self.tail = self.tail.next
        
            
    def unlink_cur_node(self, node):
        """Removes a specified node from the list
        """
        if self.head is node:
            self.head = node.next
            if node.next:
                node.next.prev = None
            return

        # Removing the node from the middle of the list
        prev_node, next_node = node.prev, node.next
        prev_node.next = next_node    
        next_node.prev = prev_node
        

        
    def get(self, key):
        """Fetches value for a specific key from the linked list

        :param key: Node identifier of any type
        :return: Node value
        """
        if key not in self.search:
            return -1
        
        node = self.search[key] 
        
        if node is not self.tail:
            self.unlink_cur_node(node)
            self.append_new_node(node)

        return node.val
    
    
    def put(self, key, value):
        """Adds a new node to the cache

        :param key: Key for the node
        :param value: Value for the node
        """
        if key in self.search:
            self.search[key].val = value
            self.get(key)
            return
        
                
        if len(self.search) == self.capacity:
            # Remove the head node and the corresponding key
            self.search.pop(self.head.key)
            self.remove_head()
        
        # Add the new node, key to the hashmap
        new_node = Node(val=value, key=key)
        self.search[key] = new_node
        self.append_new_node(new_node)

class BotCache:
    
    def __init__(self):
        self.prefixes = LRUCache(512)

    def set_prefix_cache():
        pass
    
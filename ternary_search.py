from dataclasses import dataclass


@dataclass
class TSTNode:
    """
    Node in a Ternary Search Tree.
    """
    char: str
    left: object = None
    mid: object = None
    right: object = None
    is_end: bool = False
    record_ids: object = None


class TernarySearch:
    """
    Ternary Search Tree (TST) used for prefix searching.
    """

    def __init__(self):
        self.root = None

    def insert(self, key, record_id):
        """
        Insert a key and associated record_id into the tree.
        """
        if key is None:
            key = ""

        key = key.strip()

        if key == "":
            return

        self.root = self.insert_node(self.root, key, 0, record_id)

    def prefix_search(self, prefix, limit=50):
        """
        Return record_ids for keys that start with 'prefix'.
        """
        if prefix is None:
            prefix = ""

        prefix = prefix.strip()

        if prefix == "":
            return []

        if self.root is None:
            return []

        node = self.get_node(self.root, prefix, 0)

        if node is None:
            return []

        matches = []

        # If the prefix itself is a full key
        if node.is_end:
            if node.record_ids is not None:
                i = 0
                while i < len(node.record_ids):
                    matches.append(node.record_ids[i])
                    i += 1

        # Collect all words under this prefix
        self.collect(node.mid, matches, limit)

        return matches[:limit]

    def insert_node(self, node, key, index, record_id):
        """
        Recursive helper that inserts characters one at a time.
        """
        current_char = key[index]

        if node is None:
            node = TSTNode(current_char)

        if current_char < node.char:
            node.left = self.insert_node(node.left, key, index, record_id)

        elif current_char > node.char:
            node.right = self.insert_node(node.right, key, index, record_id)

        else:
            # Characters match
            if index == len(key) - 1:
                node.is_end = True

                if node.record_ids is None:
                    node.record_ids = []

                node.record_ids.append(record_id)

            else:
                node.mid = self.insert_node(node.mid, key, index + 1, record_id)

        return node

    def get_node(self, node, key, index):
        """
        Navigate the tree to find the node corresponding to the last
        character of 'key'.
        """
        if node is None:
            return None

        current_char = key[index]

        if current_char < node.char:
            return self.get_node(node.left, key, index)

        if current_char > node.char:
            return self.get_node(node.right, key, index)

        # Characters match
        if index == len(key) - 1:
            return node

        return self.get_node(node.mid, key, index + 1)

    def collect(self, node, output_list, limit):
        """
        Collect record_ids from subtree starting at node.

        This performs a depth-first traversal:
        - left subtree
        - current node
        - mid subtree
        - right subtree
        """
        if node is None:
            return

        if len(output_list) >= limit:
            return

        # Traverse left subtree
        self.collect(node.left, output_list, limit)

        if len(output_list) >= limit:
            return

        # If this node ends a key, add its record IDs
        if node.is_end:
            if node.record_ids is not None:
                i = 0
                while i < len(node.record_ids):
                    output_list.append(node.record_ids[i])

                    if len(output_list) >= limit:
                        return

                    i += 1

        # Traverse middle subtree
        self.collect(node.mid, output_list, limit)

        if len(output_list) >= limit:
            return

        # Traverse right subtree
        self.collect(node.right, output_list, limit)

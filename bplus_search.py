from dataclasses import dataclass


@dataclass
class BPlusLeaf:
    """
    Leaf node in a B+ tree.
    """
    keys: list
    values: list
    next: object = None


@dataclass
class BPlusInternal:
    """
    Internal node in a B+ tree.
    """
    keys: list
    children: list


class BPlusTree:
    """
    Minimal B+ Tree (demo implementation).
    """

    def __init__(self, order=6):
        # order controls how many keys a node can hold before splitting.
        if order < 3:
            raise ValueError("order must be >= 3")

        self.order = order
        self.root = BPlusLeaf(keys=[], values=[])

    def insert(self, key, record_id):
        """
        Insert a (key -> record_id) entry into the tree.

        If inserting causes the root to split, create a new root internal node.
        """
        split = self.insert_node(self.root, key, record_id)

        if split is not None:
            split_key = split[0]
            left = split[1]
            right = split[2]

            # New root points to two children, separated by split_key
            self.root = BPlusInternal(keys=[split_key], children=[left, right])

    def range_search(self, key_min, key_max, limit=200):
        """
        Return record_ids whose keys are in [key_min, key_max], up to 'limit' results.
        """
        if key_min > key_max:
            temp = key_min
            key_min = key_max
            key_max = temp

        leaf = self.find_leaf(self.root, key_min)
        out = []

        while leaf is not None:
            i = 0
            while i < len(leaf.keys):
                k = leaf.keys[i]
                ids = leaf.values[i]

                if k < key_min:
                    i += 1
                    continue

                if k > key_max:
                    return out[:limit]

                # Add all record_ids for this key
                j = 0
                while j < len(ids):
                    out.append(ids[j])

                    if len(out) >= limit:
                        return out[:limit]

                    j += 1

                i += 1

            leaf = leaf.next

        return out[:limit]

    def insert_node(self, node, key, record_id):
        """
        Insert into the subtree rooted at 'node'.
        """
        if isinstance(node, BPlusLeaf):
            return self.insert_leaf(node, key, record_id)

        return self.insert_internal(node, key, record_id)

    def insert_leaf(self, leaf, key, record_id):
        """
        Insert into a leaf.
        """
        i = 0
        while i < len(leaf.keys) and leaf.keys[i] < key:
            i += 1

        if i < len(leaf.keys) and leaf.keys[i] == key:
            leaf.values[i].append(record_id)
        else:
            leaf.keys.insert(i, key)
            leaf.values.insert(i, [record_id])

        # If leaf still fits, no split
        if len(leaf.keys) < self.order:
            return None

        # Split leaf
        mid = len(leaf.keys) // 2

        right_keys = leaf.keys[mid:]
        right_values = leaf.values[mid:]
        right_next = leaf.next

        right = BPlusLeaf(keys=right_keys, values=right_values, next=right_next)

        left_keys = leaf.keys[:mid]
        left_values = leaf.values[:mid]

        left = BPlusLeaf(keys=left_keys, values=left_values, next=right)

        # Promote the first key in the right leaf
        promote = right.keys[0]
        return (promote, left, right)

    def insert_internal(self, internal, key, record_id):
        """
        Insert into an internal node.

        - Find the child that should receive (key, record_id).
        - Insert there.
        - If the child splits, insert the promoted key and new child pointer.
        - If this internal node overflows, split and return promoted key upward.
        """
        i = 0
        while i < len(internal.keys) and key >= internal.keys[i]:
            i += 1

        child = internal.children[i]
        split = self.insert_node(child, key, record_id)

        if split is None:
            return None

        split_key = split[0]
        left = split[1]
        right = split[2]

        internal.children[i] = left
        internal.keys.insert(i, split_key)
        internal.children.insert(i + 1, right)

        # If internal node still fits, no split
        if len(internal.keys) < self.order:
            return None

        # Split internal node
        mid = len(internal.keys) // 2
        promote = internal.keys[mid]

        left_keys = internal.keys[:mid]
        left_children = internal.children[: mid + 1]
        left_node = BPlusInternal(keys=left_keys, children=left_children)

        right_keys = internal.keys[mid + 1 :]
        right_children = internal.children[mid + 1 :]
        right_node = BPlusInternal(keys=right_keys, children=right_children)

        return (promote, left_node, right_node)

    def find_leaf(self, node, key):
        """
        Navigate from the root down to the leaf node where 'key' would belong.
        """
        if isinstance(node, BPlusLeaf):
            return node

        i = 0
        while i < len(node.keys) and key >= node.keys[i]:
            i += 1

        next_child = node.children[i]
        return self.find_leaf(next_child, key)


class BPlusSearch:
    """
    B+ tree search wrapper (Year range search).
    """

    def __init__(self, order=6):
        self.tree = BPlusTree(order=order)

    def build(self, items):
        """
        Build the B+ tree from an iterable of (record_id, year).
        """
        for item in items:
            record_id = item[0]
            year = item[1]

            # Insert exactly as provided (no casting)
            self.tree.insert(year, record_id)

    def search_range(self, year_min, year_max, limit=200):
        """
        Return record_ids for years in [year_min, year_max].
        """
        return self.tree.range_search(year_min, year_max, limit=limit)
